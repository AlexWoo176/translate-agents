#!/usr/bin/env node
/**
 * export-docx.js — Xuất bản dịch tiếng Việt ra định dạng DOCX.
 *
 * ⚠️  SKELETON: Argument parsing và validation đã hoàn thiện.
 *     Logic export DOCX thực tế chưa được implement.
 *
 * Usage:
 *   node export-docx.js all [bookName]
 *   node export-docx.js <chapter-number> [bookName]
 *   node export-docx.js <path/to/file.html> [bookName]
 *
 * Output: ../<bookName>/docx/
 */

'use strict';

const fs   = require('fs');
const path = require('path');

// ── Tìm project root (chứa package.json) ──────────────────────────────────
function findProjectRoot(startDir) {
  let d = startDir;
  for (let i = 0; i < 10; i++) {
    if (fs.existsSync(path.join(d, 'package.json'))) return d;
    d = path.dirname(d);
  }
  return null;
}

const PROJECT_ROOT = findProjectRoot(__dirname);
if (!PROJECT_ROOT) {
  console.error('❌ Không tìm thấy thư mục gốc dự án (cần chứa package.json).');
  process.exit(1);
}

// ── Parse args ─────────────────────────────────────────────────────────────
const args = process.argv.slice(2);

if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
  console.log(`
Sử dụng: node export-docx.js <target> [bookName]

  target    : 'all', số chương (vd: 1), hoặc path file HTML
  bookName  : tên sách (mặc định: entrepreneurship)

Ví dụ:
  node export-docx.js all
  node export-docx.js all entrepreneurship
  node export-docx.js 3 entrepreneurship
  node export-docx.js ../entrepreneurship/chapter-1/05-translated/1-intro.html
`);
  process.exit(1);
}

const target   = args[0];
const bookName = args[1] || 'entrepreneurship';

// ── Resolve book directory ─────────────────────────────────────────────────
const bookDir = path.resolve(PROJECT_ROOT, '..', bookName);

if (!fs.existsSync(bookDir)) {
  console.error(`❌ Không tìm thấy thư mục sách: ${bookDir}`);
  console.error(`   Kiểm tra lại tên sách: "${bookName}"`);
  process.exit(1);
}

// ── Resolve output directory ───────────────────────────────────────────────
const docxDir = path.join(bookDir, 'docx');
if (!fs.existsSync(docxDir)) {
  fs.mkdirSync(docxDir, { recursive: true });
  console.log(`📁 Đã tạo thư mục output: ${docxDir}`);
}

// ── Collect files cần export ───────────────────────────────────────────────
function collectFiles(target) {
  // Case 1: path file HTML cụ thể
  if (target.endsWith('.html')) {
    const absPath = path.resolve(target);
    if (!fs.existsSync(absPath)) {
      console.error(`❌ Không tìm thấy file: ${absPath}`);
      process.exit(1);
    }
    return [absPath];
  }

  // Case 2: số chương
  if (/^\d+$/.test(target)) {
    const chapterDir = path.join(bookDir, `chapter-${target}`, '05-translated');
    if (!fs.existsSync(chapterDir)) {
      console.error(`❌ Không tìm thấy thư mục: ${chapterDir}`);
      console.error(`   Đảm bảo chương ${target} đã được dịch và lưu vào 05-translated/`);
      process.exit(1);
    }
    return fs.readdirSync(chapterDir)
      .filter(f => f.endsWith('.html'))
      .map(f => path.join(chapterDir, f));
  }

  // Case 3: all
  if (target === 'all') {
    const chapterDirs = fs.readdirSync(bookDir)
      .filter(d => d.startsWith('chapter-') && fs.statSync(path.join(bookDir, d)).isDirectory());

    if (chapterDirs.length === 0) {
      console.error(`❌ Không tìm thấy chapter nào trong: ${bookDir}`);
      process.exit(1);
    }

    const files = [];
    for (const chDir of chapterDirs.sort()) {
      const transDir = path.join(bookDir, chDir, '05-translated');
      if (fs.existsSync(transDir)) {
        fs.readdirSync(transDir)
          .filter(f => f.endsWith('.html'))
          .forEach(f => files.push(path.join(transDir, f)));
      }
    }
    return files;
  }

  console.error(`❌ Target không hợp lệ: "${target}"`);
  console.error(`   Dùng 'all', số chương, hoặc path file HTML.`);
  process.exit(1);
}

// ── Main ───────────────────────────────────────────────────────────────────
const filesToExport = collectFiles(target);

if (filesToExport.length === 0) {
  console.error('❌ Không tìm thấy file HTML nào để export.');
  process.exit(1);
}

console.log(`\n📋 Chuẩn bị export ${filesToExport.length} file:`);
console.log(`   Target  : ${target}`);
console.log(`   Book    : ${bookName} (${bookDir})`);
console.log(`   Output  : ${docxDir}`);
console.log('');

for (const f of filesToExport) {
  console.log(`   - ${path.relative(bookDir, f)}`);
}

// ── STUB: Export logic chưa implement ─────────────────────────────────────
console.log('\n⚠️  Export DOCX chưa được implement. Đây là skeleton.');
console.log('   Để implement: đọc agent-export.md → TODOs trong file này.');
console.log('\n✅ Skeleton chạy thành công. Không có file DOCX nào được tạo ra.');
