const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// CRX3 格式打包脚本
// 使用方法: node scripts/pack-extension.js

const EXTENSION_DIR = path.join(__dirname, '../EasyBoss ERP - Plugin');
const OUTPUT_CRX = path.join(__dirname, '../pipixia-extension.crx');
const OUTPUT_PEM = path.join(__dirname, '../extension-private-key.pem');

// 生成或读取私钥
let privateKeyPem;
if (fs.existsSync(OUTPUT_PEM)) {
    privateKeyPem = fs.readFileSync(OUTPUT_PEM);
    console.log('使用已有私钥:', OUTPUT_PEM);
} else {
    const { privateKey } = crypto.generateKeyPairSync('rsa', {
        modulusLength: 2048,
        publicKeyEncoding: { type: 'spki', format: 'pem' },
        privateKeyEncoding: { type: 'pkcs8', format: 'pem' }
    });
    privateKeyPem = privateKey;
    fs.writeFileSync(OUTPUT_PEM, privateKeyPem);
    console.log('生成新私钥:', OUTPUT_PEM);
}

// 计算目录下所有文件的哈希
function getFiles(dir, baseDir = dir) {
    const files = [];
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const fullPath = path.join(dir, entry.name);
        const relPath = path.relative(baseDir, fullPath);
        if (entry.isDirectory()) {
            files.push(...getFiles(fullPath, baseDir));
        } else if (entry.isFile()) {
            // 跳过 .crx 和 .pem 文件
            if (!relPath.endsWith('.crx') && !relPath.endsWith('.pem')) {
                files.push({ relPath, fullPath });
            }
        }
    }
    return files;
}

const files = getFiles(EXTENSION_DIR);
console.log(`打包 ${files.length} 个文件...`);

// 创建 ZIP 内容（简化版，实际应该用 archive 库）
// 这里用 Node 原生 zlib + 手动构建 ZIP 比较麻烦，改用子进程调用 chrome --pack-extension
const { execSync } = require('child_process');

try {
    // 使用 Chrome 官方打包命令（需要 Chrome/Chromium 在 PATH 中）
    const chromePaths = [
        '/usr/bin/google-chrome',
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
    ];

    let chromePath = null;
    for (const p of chromePaths) {
        if (fs.existsSync(p)) {
            chromePath = p;
            break;
        }
    }

    if (!chromePath) {
        // 尝试 which
        try {
            chromePath = execSync('which google-chrome || which chromium || which chromium-browser', { encoding: 'utf8' }).trim();
        } catch {}
    }

    if (chromePath && fs.existsSync(chromePath)) {
        console.log('使用 Chrome 打包:', chromePath);
        execSync(`"${chromePath}" --pack-extension="${EXTENSION_DIR}" --pack-extension-key="${OUTPUT_PEM}"`, { stdio: 'inherit' });
        
        // Chrome 会在扩展目录同级生成 .crx
        const generatedCrx = path.join(path.dirname(EXTENSION_DIR), path.basename(EXTENSION_DIR) + '.crx');
        if (fs.existsSync(generatedCrx)) {
            fs.copyFileSync(generatedCrx, OUTPUT_CRX);
            console.log('✅ 打包成功:', OUTPUT_CRX);
        }
    } else {
        console.log('⚠️ 未找到 Chrome，改用 crx3 npm 包打包...');
        // 备选：用 crx3 包
        packWithCrx3();
    }
} catch (err) {
    console.error('Chrome 打包失败:', err.message);
    packWithCrx3();
}

function packWithCrx3() {
    try {
        const CRX = require('crx3');
        const crx = new CRX({
            privateKey: privateKeyPem,
        });

        const zip = require('fs').createWriteStream(OUTPUT_CRX);
        const archive = require('archiver')('zip', { zlib: { level: 9 } });
        
        archive.pipe(zip);
        
        for (const f of files) {
            archive.file(f.fullPath, { name: f.relPath });
        }
        
        archive.finalize();
        
        zip.on('close', async () => {
            const zipBuffer = fs.readFileSync(OUTPUT_CRX);
            const crxBuffer = await crx.pack(zipBuffer);
            fs.writeFileSync(OUTPUT_CRX, crxBuffer);
            console.log('✅ crx3 打包成功:', OUTPUT_CRX, `(${crxBuffer.length} bytes)`);
        });
    } catch (e) {
        console.error('crx3 打包失败，请手动安装:', e.message);
        console.log('手动安装方法: chrome://extensions/ → 开发者模式 → 加载已解压的扩展程序 → 选择目录:', EXTENSION_DIR);
    }
}
