#!/usr/bin/env node
/**
 * Term Extraction Script
 * Quét các file HTML sạch (02-clean) để trích xuất các thẻ <span data-type="term">.
 * Đối chiếu với glossary.csv gốc. Nếu có thì lấy luôn bản dịch (status = approved).
 * Nếu không có, để trống (status = proposal) để LLM điền.
 * Nếu là tên riêng (no-emphasis), tự động bê nguyên gốc (notes = Tên riêng).
 * 
 * Usage:
 *   node term-extract.js 1
 */

const fs = require('fs');
const path = require('path');

// ── Configuration ────────────────────────────────────────────────────────
function findProjectRoot(currentDir) {
    let d = currentDir;
    for (let i = 0; i < 10; i++) {
        if (fs.existsSync(path.join(d, 'package.json'))) {
            return d;
        }
        d = path.dirname(d);
    }
    return null;
}

const PROJECT_ROOT = findProjectRoot(__dirname);
if (!PROJECT_ROOT) {
    console.error("❌ Không tìm thấy thư mục gốc của dự án (cần chứa package.json).");
    process.exit(1);
}

const args = process.argv.slice(2);
if (args.length < 2 || args[0] === '--help' || args[0] === '-h') {
    console.log(`Usage: node term-extract.js <book-name> <chapter-number>`);
    process.exit(0);
}

const bookName = args[0];
const chapterNum = args[1];

let DATA_DIR = path.join(PROJECT_ROOT, '..', 'books', bookName);
if (!fs.existsSync(DATA_DIR)) {
    DATA_DIR = path.join(PROJECT_ROOT, '..', bookName);
    if (!fs.existsSync(DATA_DIR) && bookName === 'statistics') {
        DATA_DIR = path.join(PROJECT_ROOT, '..', 'book-statistics');
    }
}
const GLOSSARY_FILE = path.join(DATA_DIR, 'glossary.csv');

// ── Csv Parser ───────────────────────────────────────────────────────────
function parseCsvLine(text) {
    const result = [];
    let cur = '';
    let inQuotes = false;
    for (let i = 0; i < text.length; i++) {
        const c = text[i];
        if (c === '"') {
            if (inQuotes && text[i + 1] === '"') {
                cur += '"';
                i++;
            } else {
                inQuotes = !inQuotes;
            }
        } else if (c === ',' && !inQuotes) {
            result.push(cur);
            cur = '';
        } else {
            cur += c;
        }
    }
    result.push(cur);
    return result;
}

function loadGlossary() {
    const glossaryMap = new Map();
    if (!fs.existsSync(GLOSSARY_FILE)) {
        console.warn("⚠️ Không tìm thấy glossary.csv tại:", GLOSSARY_FILE);
        return glossaryMap;
    }
    
    let content = fs.readFileSync(GLOSSARY_FILE, 'utf-8');
    if (content.charCodeAt(0) === 0xFEFF) {
        content = content.slice(1);
    }
    
    const lines = content.split(/\r?\n/).filter(line => line.trim() !== '');
    // Bỏ header
    for (let i = 1; i < lines.length; i++) {
        const row = parseCsvLine(lines[i]);
        if (row.length >= 2) {
            const key = row[0].trim().toLowerCase();
            if (key) {
                glossaryMap.set(key, {
                    translation: row[1] ? row[1].trim() : "",
                    options: row[2] ? row[2].trim() : "",
                    desc_en: row[3] ? row[3].trim() : "",
                    desc_vi: row[4] ? row[4].trim() : ""
                });
            }
        }
    }
    return glossaryMap;
}

// ── Helper ───────────────────────────────────────────────────────────────
function stripHtml(text) {
    return text.replace(/<[^>]+>/g, '').trim();
}

function extractTermsFromHtml(html) {
    const terms = new Map();
    
    const termRegex = /<span\s+([^>]*?data-type="term"[^>]*)>(.*?)<\/span>/gi;
    let match;
    
    while ((match = termRegex.exec(html)) !== null) {
        const attrs = match[1];
        const innerText = stripHtml(match[2]).trim();
        const keyLower = innerText.toLowerCase();
        
        if (!keyLower) continue;
        
        const isNoEmphasis = attrs.includes('no-emphasis');
        
        if (!terms.has(keyLower)) {
            terms.set(keyLower, {
                key: innerText,
                isNoEmphasis: isNoEmphasis
            });
        } else {
            if (isNoEmphasis) {
                const existing = terms.get(keyLower);
                existing.isNoEmphasis = true;
            }
        }
    }
    
    return Array.from(terms.values());
}

function escapeCsv(str) {
    if (!str) return '""';
    const escaped = str.replace(/"/g, '""');
    return `"${escaped}"`;
}

function padRight(str, length) {
    return str.padEnd(length, ' ');
}

// ── Main Logic ───────────────────────────────────────────────────────────
function runExtraction(chapterNum) {
    const chapterDir = path.join(DATA_DIR, `chapter-${chapterNum}`);
    const cleanDir = path.join(chapterDir, '02-clean');
    const outDir = path.join(chapterDir, '03-analyzed');
    
    if (!fs.existsSync(cleanDir)) {
        console.error(`⚠️ Không tìm thấy thư mục: ${cleanDir}`);
        return;
    }
    
    const htmlFiles = fs.readdirSync(cleanDir).filter(f => f.endsWith('.html'));
    if (htmlFiles.length === 0) {
        console.error(`⚠️ Không có file HTML nào trong: ${cleanDir}`);
        return;
    }
    
    console.log(`\n============================================================`);
    console.log(`  TRÍCH XUẤT THUẬT NGỮ CHƯƠNG ${chapterNum} — ${htmlFiles.length} files`);
    console.log(`============================================================`);
    
    const glossaryMap = loadGlossary();
    console.log(`  📚 Đã nạp ${glossaryMap.size} thuật ngữ từ glossary.csv gốc.`);
    
    const allTermsMap = new Map();
    
    for (const file of htmlFiles) {
        const filePath = path.join(cleanDir, file);
        const html = fs.readFileSync(filePath, 'utf-8');
        
        const terms = extractTermsFromHtml(html);
        
        for (const t of terms) {
            const keyLower = t.key.toLowerCase();
            if (!allTermsMap.has(keyLower)) {
                allTermsMap.set(keyLower, t);
            }
        }
    }
    
    const allTerms = Array.from(allTermsMap.values()).sort((a, b) => a.key.localeCompare(b.key));
    
    if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
    const outCsvPath = path.join(outDir, `chapter-${chapterNum}-new-glossary.csv`);
    
    let csvContent = `key,translation,options,desc_en,desc_vi,chapter,status,notes\n`;
    
    let noEmphasisCount = 0;
    let approvedCount = 0;
    let proposalCount = 0;
    
    // Tìm độ dài dài nhất để căn chỉnh cột cho đẹp (như người dùng muốn)
    let maxKeyLen = 3;
    let maxTransLen = 11;
    for (const t of allTerms) {
        if (t.key.length > maxKeyLen) maxKeyLen = t.key.length;
        if (t.isNoEmphasis) {
            if (t.key.length > maxTransLen) maxTransLen = t.key.length;
        } else if (glossaryMap.has(t.key.toLowerCase())) {
            const tr = glossaryMap.get(t.key.toLowerCase()).translation;
            if (tr.length > maxTransLen) maxTransLen = tr.length;
        }
    }
    // padding for quotes
    maxKeyLen += 2; 
    maxTransLen += 2;
    
    for (const t of allTerms) {
        const keyLower = t.key.toLowerCase();
        let translation = "";
        let options = "";
        let desc_en = "";
        let desc_vi = "";
        let status = "proposal";
        let notes = "";
        
        if (t.isNoEmphasis) {
            translation = t.key;
            status = "approved"; // Hoặc có thể để nguyên gốc
            notes = "Tên riêng, không dịch";
            noEmphasisCount++;
        } else if (glossaryMap.has(keyLower)) {
            const hit = glossaryMap.get(keyLower);
            translation = hit.translation;
            options = hit.options;
            desc_en = hit.desc_en;
            desc_vi = hit.desc_vi;
            status = "approved";
            approvedCount++;
        } else {
            proposalCount++;
        }
        
        const paddedKey = padRight(escapeCsv(keyLower), maxKeyLen);
        const paddedTrans = padRight(escapeCsv(translation), maxTransLen);
        
        csvContent += `${paddedKey}, ${paddedTrans}, ${escapeCsv(options)}, ${escapeCsv(desc_en)}, ${escapeCsv(desc_vi)}, ${chapterNum}, ${padRight('"' + status + '"', 10)}, ${escapeCsv(notes)}\n`;
    }
    
    fs.writeFileSync(outCsvPath, '\uFEFF' + csvContent, 'utf-8');
    
    console.log(`\n  ✅ Tổng hợp toàn chương: ${allTerms.length} thuật ngữ.`);
    console.log(`     - Tên riêng (no-emphasis)   : ${noEmphasisCount}`);
    console.log(`     - Đã có trong glossary chuẩn: ${approvedCount}`);
    console.log(`     - Cần AI đề xuất (proposal) : ${proposalCount}`);
    console.log(`\n  💾 Đã lưu danh sách thuật ngữ nháp vào:`);
    console.log(`     ${outCsvPath}`);
}

runExtraction(chapterNum);
