const executablePath="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";//浏览器地址，这个要替换成本地的

const [,, codeString, functionName, argsJSON] = process.argv;
const puppeteer = require("puppeteer-core");
const path = require("path");

const decodedCode = JSON.parse(codeString);
const argsDict = JSON.parse(argsJSON);

const frontendPage='jsts.html'

const orderedArgs = Object.values(argsDict);

(async () => {
  const browser = await puppeteer.launch({
    executablePath: executablePath,
    headless: "new",
    args: ["--no-sandbox"],
    defaultViewport: { width: 800, height: 600 }
  });

  const page = await browser.newPage();
  const fileUrl = "file://" + path.resolve(__dirname, frontendPage);

  page.on('console', msg => {
    console.log(`[页面 console] ${msg.text()}`);
  });

  await page.goto(fileUrl, { waitUntil: "networkidle0" });

  const result = await page.evaluate((code, funcName, orderedArgs) => {
    try {
      // 构造参数
      const args = orderedArgs.map(arg => {
        if (arg && typeof arg === 'object' && '__js__' in arg) {
          try {
            eval(arg.__js__);
            const match = arg.__js__.match(/function\s+([a-zA-Z0-9_]+)/);
            const func = eval(match[1]);
            return typeof func === 'function' ? func() : func;
          } catch (e) {
            return arg; // fallback
          }
        }
        return arg;
      });
      // 执行函数
      eval(code);  // 定义函数
      const fn = eval(funcName);  // 获取函数
      const rawResult = fn(...args);
      if (rawResult && typeof rawResult.getCoordinates === 'function') {
          const coords = rawResult.getCoordinates().map(c => [c.x, c.y]);
          const type = rawResult.getGeometryType();
          return { type, coordinates: coords };
      }

      return rawResult; // 普通类型直接返回
    } catch (e) {
      return { error: e.message };
    }
  }, decodedCode, functionName, orderedArgs);
    console.log(JSON.stringify({result}))


  await browser.close();
})();