const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  // Navigate to the example portfolio
  await page.goto('https://pujasridhar.github.io/');
  
  // Wait for the page to load
  await page.waitForLoadState('networkidle');
  
  // Get the page content
  const html = await page.content();
  
  // Save HTML to file
  const fs = require('fs');
  fs.writeFileSync('example-portfolio.html', html);
  
  // Get some basic info
  const title = await page.title();
  const bodyText = await page.locator('body').innerText();
  
  console.log('Page Title:', title);
  console.log('\nBody Text Preview (first 2000 chars):');
  console.log(bodyText.substring(0, 2000));
  
  // Get styles
  const styles = await page.evaluate(() => {
    const allStyles = [];
    const sheets = document.styleSheets;
    
    for (let sheet of sheets) {
      try {
        const rules = sheet.cssRules || sheet.rules;
        for (let rule of rules) {
          if (rule.cssText) {
            allStyles.push(rule.cssText);
          }
        }
      } catch (e) {
        // Ignore cross-origin styles
      }
    }
    
    return allStyles.slice(0, 100); // Limit to first 100 rules
  });
  
  console.log('\nFirst 20 CSS rules:');
  styles.slice(0, 20).forEach((style, i) => {
    console.log(`${i + 1}. ${style.substring(0, 150)}${style.length > 150 ? '...' : ''}`);
  });
  
  await browser.close();
})();