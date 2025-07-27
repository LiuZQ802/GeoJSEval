// 加载代码和测试用例
const [,, codeString, functionName, argsJSON] = process.argv;

// 加载所需库
try { globalThis.turf = require('@turf/turf'); } catch {}
try { globalThis.geolib = require('geolib');} catch (e) {}
try { turf.buffer = require('@turf/buffer').default; } catch {}
try { turf.booleanTouches = require('@turf/boolean-touches').default; } catch {}
try { turf.convertArea = require('@turf/helpers').convertArea; } catch {}
try { turf.clusterEach = require('@turf/clusters').clusterEach; } catch {}

const decodedCode = JSON.parse(codeString); // 支持传入字符串中带换行和引号
const argsDict = JSON.parse(argsJSON);

if (argsDict.callback && typeof argsDict.callback === 'string') {
    argsDict.callback = eval(argsDict.callback);
}
const orderedArgs = Object.values(argsDict);

const args = orderedArgs.map(arg => {
    if (arg && typeof arg === 'object' && '__js__' in arg) {
        try {
            eval(arg.__js__);
            const match = arg.__js__.match(/function\s+([a-zA-Z0-9_]+)/);
            const func = eval(match[1]);
            return typeof func === 'function' ? func() : func;
        } catch (e) {
            console.log(e)
            return arg; // fallback
        }
    }
    return arg;
});
// 注入函数定义
eval(decodedCode);


// 获取函数对象并调用
const targetFunc = eval(functionName);
const result = targetFunc(...args);
console.log(JSON.stringify({ result }));

