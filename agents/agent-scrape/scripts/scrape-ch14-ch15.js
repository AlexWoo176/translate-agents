const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const RAW_DIR = path.join(__dirname, '../../../../entrepreneurship/raw');

const CHAPTER_14_LINKS = [
  'https://openstax.org/books/entrepreneurship/pages/14-introduction',
  'https://openstax.org/books/entrepreneurship/pages/14-1-types-of-resources',
  'https://openstax.org/books/entrepreneurship/pages/14-2-using-the-pest-framework-to-assess-resource-needs',
  'https://openstax.org/books/entrepreneurship/pages/14-3-managing-resources-over-the-venture-life-cycle',
  'https://openstax.org/books/entrepreneurship/pages/14-key-terms',
  'https://openstax.org/books/entrepreneurship/pages/14-summary',
  'https://openstax.org/books/entrepreneurship/pages/14-review-questions',
  'https://openstax.org/books/entrepreneurship/pages/14-discussion-questions',
  'https://openstax.org/books/entrepreneurship/pages/14-case-questions',
  'https://openstax.org/books/entrepreneurship/pages/14-suggested-resources',
];

const CHAPTER_15_LINKS = [
  'https://openstax.org/books/entrepreneurship/pages/15-introduction',
  'https://openstax.org/books/entrepreneurship/pages/15-1-launching-your-venture',
  'https://openstax.org/books/entrepreneurship/pages/15-2-making-difficult-business-decisions-in-response-to-challenges',
  'https://openstax.org/books/entrepreneurship/pages/15-3-seeking-help-or-support',
  'https://openstax.org/books/entrepreneurship/pages/15-4-now-what-serving-as-a-mentor-consultant-or-champion',
  'https://openstax.org/books/entrepreneurship/pages/15-5-reflections-documenting-the-journey',
  'https://openstax.org/books/entrepreneurship/pages/15-key-terms',
  'https://openstax.org/books/entrepreneurship/pages/15-summary',
  'https://openstax.org/books/entrepreneurship/pages/15-review-questions',
  'https://openstax.org/books/entrepreneurship/pages/15-discussion-questions',
  'https://openstax.org/books/entrepreneurship/pages/15-case-questions',
  'https://openstax.org/books/entrepreneurship/pages/15-suggested-resources',
];

const ALL_LINKS = [...CHAPTER_14_LINKS, ...CHAPTER_15_LINKS];

if (!fs.existsSync(RAW_DIR)) {
  fs.mkdirSync(RAW_DIR, { recursive: true });
}

async function scrapeChapters() {
  console.log('Khởi động trình duyệt...');
  const browser = await puppeteer.launch({ headless: "new" });
  const page = await browser.newPage();
  
  try {
    console.log(`Sẽ scrape ${ALL_LINKS.length} trang cho chapter 14 và 15...`);

    for (let i = 0; i < ALL_LINKS.length; i++) {
      const link = ALL_LINKS[i];
      const fileName = link.split('/').pop() + '.html';
      const filePath = path.join(RAW_DIR, fileName);

      console.log(`[${i + 1}/${ALL_LINKS.length}] Đang tải (raw): ${fileName}`);
      
      await page.goto(link, { waitUntil: 'networkidle2' });
      const html = await page.content();
      
      fs.writeFileSync(filePath, html, 'utf8');
      await new Promise(r => setTimeout(r, 1000));
    }

    console.log('✅ Hoàn tất quá trình thu thập chapter 14 và 15!');

  } catch (error) {
    console.error('❌ Lỗi trong quá trình thu thập:', error);
  } finally {
    await browser.close();
  }
}

scrapeChapters();
