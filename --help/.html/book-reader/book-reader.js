document.addEventListener('DOMContentLoaded', () => {
  // 1. Restructure DOM
  const body = document.body;
  const mainContent = document.createElement('div');
  mainContent.id = 'br-main-content';

  // Move all existing children of body into mainContent
  while (body.firstChild) {
    mainContent.appendChild(body.firstChild);
  }

  // Create Right Panel
  const rightPanel = document.createElement('div');
  rightPanel.id = 'br-right-panel';
  rightPanel.innerHTML = `
    <div id="br-panel-header" style="padding: 15px 20px; border-bottom: 1px solid #e1e4e8; background: #fff; display: flex; justify-content: space-between; align-items: center; gap: 10px;">
      <div style="display: flex; gap: 5px;">
        <button id="br-prev-btn" title="Previous" style="background: #e1e4e8; color: #333; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-weight: bold;">&larr;</button>
        <button id="br-next-btn" title="Next" style="background: #e1e4e8; color: #333; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-weight: bold;">&rarr;</button>
      </div>
      <h3 style="margin: 0; font-size: 1.1rem; color: #333; flex-grow: 1; text-align: center;">Book Reader</h3>
      <button id="br-swap-btn" style="background: #0366d6; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-weight: bold;">Swap to EN</button>
    </div>
    <div id="br-eng-section">
      <div id="br-eng-content">Hover over the text to see the translation here.</div>
    </div>
    <div id="br-term-section">
      <div id="br-term-details">Hover over a highlighted term to see details.</div>
    </div>
  `;

  // Append back to body
  body.appendChild(mainContent);
  body.appendChild(rightPanel);

  // 2. Fetch and parse Glossary
  let glossaryData = [];
  const glossaryPath = '../../glossary.csv';

  function parseCSV(text) {
    const lines = text.split('\n').filter(line => line.trim() !== '');
    if (lines.length === 0) return [];
    const headers = lines[0].split(',').map(h => h.trim());
    return lines.slice(1).map(line => {
      const values = [];
      let inQuotes = false;
      let currentValue = '';
      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"' && line[i+1] === '"') {
          currentValue += '"';
          i++; 
        } else if (char === '"') {
          inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
          values.push(currentValue.trim());
          currentValue = '';
        } else {
          currentValue += char;
        }
      }
      values.push(currentValue.trim());
      
      const obj = {};
      headers.forEach((header, index) => {
        obj[header] = values[index] || '';
      });
      return obj;
    });
  }

  fetch(glossaryPath)
    .then(response => {
      if (!response.ok) throw new Error("Network response was not ok");
      return response.text();
    })
    .then(csvText => {
      glossaryData = parseCSV(csvText);
    })
    .catch(err => console.error('Error fetching glossary:', err));

  // 3. Highlight Terms by default
  const termElements = mainContent.querySelectorAll('[data-type="term"]');
  termElements.forEach(el => {
    el.classList.add('br-highlight-term');
  });

  // 4. State for EN/VN mode
  let isEnMode = false;
  const swapBtn = document.getElementById('br-swap-btn');
  const readingTitle = document.getElementById('br-reading-title');
  const engContentPanel = document.getElementById('br-eng-content');
  const termDetailsContainer = document.getElementById('br-term-details');

  swapBtn.addEventListener('click', () => {
    isEnMode = !isEnMode;
    if (isEnMode) {
      document.body.classList.add('lang-swap');
      swapBtn.textContent = 'Swap to VN';
      readingTitle.textContent = 'Vietnamese Translation';
    } else {
      document.body.classList.remove('lang-swap');
      swapBtn.textContent = 'Swap to EN';
      readingTitle.textContent = 'Original English';
    }
    // Clear panels on swap
    engContentPanel.innerHTML = 'Hover over the text to see the translation here.';
    termDetailsContainer.innerHTML = 'Hover over a highlighted term to see details.';
  });

  // 4.5 Navigation Logic
  let chapterFiles = [];
  let currentIndex = -1;
  
  if (window.BOOK_PAGES && window.BOOK_PAGES.length > 0) {
    chapterFiles = window.BOOK_PAGES;
    const currentPath = window.location.pathname;
    currentIndex = chapterFiles.findIndex(page => {
        const cleanPage = page.replace('../../', '');
        return currentPath.endsWith(cleanPage);
    });
  } else {
    // Fallback for local testing without build script
    chapterFiles = [
      '1-introduction.html',
      '1-1-entrepreneurship-today.html',
      '1-2-entrepreneurial-vision-and-goals.html',
      '1-3-the-entrepreneurial-mindset.html',
      '1-key-terms.html',
      '1-summary.html',
      '1-review-questions.html',
      '1-discussion-questions.html',
      '1-case-questions.html',
      '1-suggested-resources.html'
    ];
    const pathParts = window.location.pathname.split('/');
    const currentFile = pathParts[pathParts.length - 1] || '1-introduction.html';
    currentIndex = chapterFiles.indexOf(currentFile);
  }
  
  const prevBtn = document.getElementById('br-prev-btn');
  const nextBtn = document.getElementById('br-next-btn');
  
  if (currentIndex <= 0) prevBtn.disabled = true;
  if (currentIndex === -1 || currentIndex >= chapterFiles.length - 1) nextBtn.disabled = true;
  if (prevBtn.disabled) prevBtn.style.opacity = '0.5';
  if (nextBtn.disabled) nextBtn.style.opacity = '0.5';

  function navigateTo(url) {
    document.body.classList.add('br-fade-out');
    setTimeout(() => {
      window.location.href = url;
    }, 150);
  }

  prevBtn.addEventListener('click', () => {
    if (currentIndex > 0) navigateTo(chapterFiles[currentIndex - 1]);
  });
  nextBtn.addEventListener('click', () => {
    if (currentIndex > -1 && currentIndex < chapterFiles.length - 1) navigateTo(chapterFiles[currentIndex + 1]);
  });

  // Keyboard Navigation
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'ArrowLeft') {
      if (currentIndex > 0) navigateTo(chapterFiles[currentIndex - 1]);
    } else if (e.key === 'ArrowRight') {
      if (currentIndex > -1 && currentIndex < chapterFiles.length - 1) navigateTo(chapterFiles[currentIndex + 1]);
    }
  });

  // 5. Event Delegation for Hovers
  mainContent.addEventListener('mouseover', (e) => {
    
    // Handle term hover
    const termEl = e.target.closest('[data-type="term"]');
    if (termEl) {
      let englishTermText = '';
      let vnText = '';
      const termId = termEl.getAttribute('id');

      if (isEnMode && termEl.closest('.eng')) {
         englishTermText = termEl.textContent.trim().toLowerCase();
      } else if (!isEnMode && termEl.closest('.vn')) {
         vnText = termEl.textContent.trim().toLowerCase();
         
         const parentVn = termEl.closest('.vn.visible');
         if (parentVn) {
             const vnId = parentVn.id;
             if (vnId && vnId.endsWith('-vn')) {
                 const engId = vnId.replace('-vn', '');
                 const engEl = document.getElementById(engId);
                 if (engEl) {
                     const engTermEl = engEl.querySelector(`[id="${termId}"]`) || engEl.querySelector(`[data-type="term"]`);
                     if (engTermEl) englishTermText = engTermEl.textContent.trim().toLowerCase();
                 }
             }
         }
         if (!englishTermText && termId) {
             const all = document.querySelectorAll(`[id="${termId}"]`);
             if (all.length > 0) {
                 englishTermText = all[0].textContent.trim().toLowerCase(); 
             }
         }
      }

      if (englishTermText || vnText) {
          let matchedTerm = null;
          if (englishTermText) {
            matchedTerm = glossaryData.find(item => item.key && item.key.toLowerCase() === englishTermText);
          }
          if (!matchedTerm) {
             matchedTerm = glossaryData.find(item => 
                (item.translation && item.translation.toLowerCase() === vnText) || 
                (item.key && item.key.toLowerCase() === vnText) ||
                (englishTermText && item.key && item.key.toLowerCase() === englishTermText)
             );
          }

          if (matchedTerm) {
            termDetailsContainer.innerHTML = `
              <div class="br-term-card">
                <h3>${matchedTerm.key}</h3>
                <div class="br-vi">VN: ${matchedTerm.translation}</div>
                <div class="br-desc-en"><strong>EN Desc:</strong> ${matchedTerm.desc_en || 'N/A'}</div>
                <div class="br-desc-vi"><strong>VN Desc:</strong> ${matchedTerm.desc_vi || 'N/A'}</div>
              </div>
            `;
          } else {
            termDetailsContainer.innerHTML = `
              <div class="br-term-card">
                <h3>${englishTermText || vnText}</h3>
                <div>No matching definition found in glossary.</div>
              </div>
            `;
          }
      }
    }

    // Handle block hover for translation
    const blockEl = e.target.closest('.vn.visible, .eng.hidden');
    if (blockEl) {
        if (!isEnMode && blockEl.classList.contains('vn')) {
          const vnId = blockEl.getAttribute('id');
          if (vnId && vnId.endsWith('-vn')) {
            const engId = vnId.replace('-vn', '');
            const engEl = document.getElementById(engId);
            if (engEl) engContentPanel.innerHTML = engEl.outerHTML;
            else engContentPanel.innerHTML = "<em>English counterpart not found.</em>";
          } else {
            const prev = blockEl.previousElementSibling;
            if (prev && prev.classList.contains('eng')) engContentPanel.innerHTML = prev.outerHTML;
          }
        } else if (isEnMode && blockEl.classList.contains('eng')) {
          const engId = blockEl.getAttribute('id');
          if (engId && !engId.endsWith('-vn')) {
            const vnId = engId + '-vn';
            const vnEl = document.getElementById(vnId);
            if (vnEl) engContentPanel.innerHTML = vnEl.outerHTML;
            else {
                const next = blockEl.nextElementSibling;
                if (next && next.classList.contains('vn')) engContentPanel.innerHTML = next.outerHTML;
                else engContentPanel.innerHTML = "<em>Vietnamese counterpart not found.</em>";
            }
          } else {
            const next = blockEl.nextElementSibling;
            if (next && next.classList.contains('vn')) engContentPanel.innerHTML = next.outerHTML;
          }
        }
    }
  });

});
