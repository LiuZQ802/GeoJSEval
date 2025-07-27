const executablePath="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";//浏览器地址，这个要替换成本地的

const [,, codeString, functionName, argsJSON,case_name,pic_path,type,eval_method] = process.argv;

const puppeteer = require("puppeteer-core");
const path = require("path");

const decodedCode = JSON.parse(codeString);
const argsDict = JSON.parse(argsJSON);
const eval_method_list = JSON.parse(eval_method);
if ('map' in argsDict) {
  const val = argsDict['map'];
  if(val === true){
    argsDict['map']='__INJECT_MAP__'
  }
}
let frontendPage='leaflet.html'
let outputPath=''
if(type==='leaflet'){
    frontendPage='leaflet.html'
    outputPath=path.resolve(pic_path, case_name+'.png');
}else if (type==='openlayers'){
    frontendPage='openlayers.html'
    outputPath=path.resolve(pic_path, case_name+'.png');
}
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

  const result = await page.evaluate((code, funcName, orderedArgs,eval_method_list) => {
    try {
      // 获取地图实例
      const map = typeof window.getMapInstance === 'function' ? window.getMapInstance() : null;

      // 构造参数
      const args = orderedArgs.map(arg => {
        if (arg === '__INJECT_MAP__') {
          return map;
        }
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
      const result =fn(...args);
      if (Array.isArray(eval_method_list) && eval_method_list.length === 0) {
          return result
      }
      const evalResults = {};
      for (const expr of eval_method_list) {
          try {
              const cleanedExpr = expr.includes('.') ? expr.split('.').slice(1).join('.') : expr;
              const value = Function("result", `return result.${cleanedExpr}`)(result);
              evalResults[expr] = value;
          } catch (e) {
              evalResults[expr] = { error: e.message };
          }
      }
      return evalResults
    } catch (e) {
      return { error: e.message };
    }
  }, decodedCode, functionName, orderedArgs,eval_method_list);

    await page.screenshot({ path: outputPath });
    console.log(JSON.stringify({result}))


  await browser.close();
})();