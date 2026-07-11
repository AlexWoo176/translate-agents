const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');

function prepFile(inFile, outFile) {
    const html = fs.readFileSync(inFile, 'utf-8');
    const $ = cheerio.load(html);

    // Add style if not exists
    if ($('head style').length === 0) {
        $('head').append('\n<style>\n.eng.hidden { display: none; }\n.vn.visible { color: #000; }\n</style>\n');
    }

    const tagsToDuplicate = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'caption', 'figcaption', 'th', 'td', 'div.os-caption-container'];

    tagsToDuplicate.forEach(tagName => {
        $(tagName).each(function() {
            const el = $(this);
            
            // Check if it contains another duplicatable tag
            let containsBlock = false;
            for (const childTag of tagsToDuplicate) {
                if (el.find(childTag).length > 0) {
                    containsBlock = true;
                    break;
                }
            }
            
            if (containsBlock) return;
            
            // Skip if already prepped
            if (el.hasClass('eng') && el.hasClass('hidden')) return;
            if (el.hasClass('vn') && el.hasClass('visible')) return;

            const clone = el.clone();

            // Modify original
            el.addClass('eng hidden');

            // Modify clone
            clone.removeClass('eng hidden');
            clone.addClass('vn visible');
            
            if (clone.attr('id')) {
                clone.attr('id', clone.attr('id') + '-vn');
            }

            el.after(clone);
        });
    });

    fs.mkdirSync(path.dirname(outFile), { recursive: true });
    fs.writeFileSync(outFile, $.html());
    console.log(`Prepped ${outFile}`);
}

const inFile = process.argv[2];
const outFile = process.argv[3];
if (inFile && outFile) {
    prepFile(inFile, outFile);
} else {
    console.log('Usage: node prep_html.js <inFile> <outFile>');
}
