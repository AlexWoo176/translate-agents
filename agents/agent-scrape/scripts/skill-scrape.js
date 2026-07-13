const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'https://openstax.org';

const bookName = process.argv[2];
const startUrl = process.argv[3];

if (!bookName || !startUrl) {
  console.error("Vui lòng cung cấp tên sách và URL bắt đầu! Ví dụ: node skills/skill-scrape.js entrepreneurship https://openstax.org/books/entrepreneurship/pages/1-introduction");
  process.exit(1);
}

const PROJECT_ROOT = path.resolve(__dirname, '../../..');

function loadEnv() {
  const envPath = path.join(PROJECT_ROOT, '.env');
  const env = {};
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf-8');
    content.split(/\r?\n/).forEach(line => {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        const parts = trimmed.split('=');
        if (parts.length >= 2) {
          env[parts[0].trim()] = parts.slice(1).join('=').trim();
        }
      }
    });
  }
  return env;
}

const BOOK_URL = startUrl;
const env = loadEnv();
const booksRoot = env.BOOKS_ROOT || path.join(PROJECT_ROOT, '..', 'books');
const dataRoot = path.isAbsolute(booksRoot) ? path.join(booksRoot, bookName) : path.resolve(PROJECT_ROOT, booksRoot, bookName);
const RAW_DIR = path.join(dataRoot, 'raw');

if (!fs.existsSync(RAW_DIR)) {
  fs.mkdirSync(RAW_DIR, { recursive: true });
}

async function scrapeBook() {
  console.log('Khởi động trình duyệt...');
  const browser = await puppeteer.launch({ headless: "new" });
  const page = await browser.newPage();
  
  try {
    console.log(`Đang truy cập ${BOOK_URL}...`);
    await page.goto(BOOK_URL, { waitUntil: 'networkidle2' });

    console.log('Đang trích xuất các liên kết chương (TOC)...');
    const links = await page.evaluate((bookName) => {
      const aTags = Array.from(document.querySelectorAll('a'));
      const chapterLinks = new Set();
      
      aTags.forEach(a => {
        const absoluteUrl = a.href;
        if (
          absoluteUrl && 
          absoluteUrl.startsWith(`https://openstax.org/books/${bookName}/pages/`) && 
          !absoluteUrl.includes('#')
        ) {
          chapterLinks.add(absoluteUrl.split('?')[0]);
        }
      });
      return Array.from(chapterLinks);
    }, bookName);

    console.log(`Tìm thấy ${links.length} trang/chương hợp lệ.`);

    for (let i = 0; i < links.length; i++) {
      const link = links[i];
      const fileName = link.split('/').pop() + '.html';
      const filePath = path.join(RAW_DIR, fileName);

      console.log(`[${i + 1}/${links.length}] Đang tải (raw): ${fileName}`);
      
      await page.goto(link, { waitUntil: 'networkidle2' });
      const html = await page.content();
      
      fs.writeFileSync(filePath, html, 'utf8');
      await new Promise(r => setTimeout(r, 1000));
    }

    console.log('✅ Hoàn tất quá trình tải sách gốc!');

  } catch (error) {
    console.error('❌ Lỗi trong quá trình thu thập:', error);
  } finally {
    await browser.close();
  }
}

scrapeBook();
