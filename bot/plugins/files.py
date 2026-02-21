<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE html>
<html b:css='false' b:defaultwidgetversion='2' b:layoutsVersion='3' xmlns='http://www.w3.org/1999/xhtml' xmlns:b='http://www.google.com/2005/gml/b' xmlns:data='http://www.google.com/2005/gml/data' xmlns:expr='http://www.google.com/2005/gml/expr'>
<head>
    <meta charset="utf-8"/>
    <meta content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover' name='viewport'/>
    <title>Cloud Manager</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css' rel='stylesheet'/>
    <link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap' rel='stylesheet'/>

    <b:skin><![CDATA[
        :root { 
            --bg: var(--tg-theme-bg-color, #f3f4f6);
            --card: var(--tg-theme-secondary-bg-color, #ffffff);
            --text: var(--tg-theme-text-color, #1f2937);
            --sub: var(--tg-theme-hint-color, #6b7280);
            --accent: var(--tg-theme-button-color, #6366f1);
            --accent-text: var(--tg-theme-button-text-color, #ffffff);
            --danger: #ef4444; 
            --border: rgba(0,0,0,0.1);
        }
        
        body { margin: 0; font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 15px; padding-bottom: 90px; min-height: 100vh; box-sizing: border-box; user-select: none; -webkit-tap-highlight-color: transparent; }
        
        ::view-transition-old(root), ::view-transition-new(root) { animation: none; mix-blend-mode: normal; }
        ::view-transition-new(root) { z-index: 999; }

        .stats-card { background: linear-gradient(135deg, var(--accent), #4f46e5); color: var(--accent-text); padding: 20px; border-radius: 16px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .stats-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .storage-bar { background: rgba(255,255,255,0.3); height: 6px; border-radius: 10px; overflow: hidden; margin-top: 5px; }
        .storage-fill { background: #fff; height: 100%; border-radius: 10px; width: 0%; transition: width 1s cubic-bezier(0.4, 0, 0.2, 1); }
        
        .search-box { background: var(--card); padding: 12px 15px; border-radius: 12px; display: flex; align-items: center; gap: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid var(--border); }
        .search-box input { border: none; background: transparent; width: 100%; outline: none; color: var(--text); font-size: 1rem; }
        .search-box i { color: var(--sub); }
        
        .file-list { list-style: none; padding: 0; margin: 0; }
        .file-item { background: var(--card); border-radius: 12px; padding: 15px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid var(--border); transition: transform 0.1s; }
        .file-item:active { transform: scale(0.98); } 
        
        .file-icon { width: 42px; height: 42px; background: rgba(128,128,128,0.1); color: var(--accent); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.3rem; margin-right: 15px; }
        .file-info { flex: 1; min-width: 0; }
        .file-info h4 { margin: 0 0 4px 0; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text); }
        .file-info p { margin: 0; font-size: 0.75rem; color: var(--sub); }
        
        .file-actions { display: flex; gap: 5px; }
        .action-btn { background: transparent; border: none; color: var(--sub); font-size: 1.1rem; padding: 8px; cursor: pointer; border-radius: 50%; transition: 0.2s; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; }
        .action-btn:hover { background: rgba(0,0,0,0.05); color: var(--accent); }
        .action-btn.delete:hover { color: var(--danger); background: rgba(239, 68, 68, 0.1); }

        .settings-btn { position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.2); border-radius: 50%; width: 35px; height: 35px; display: flex; align-items: center; justify-content: center; color: #fff; cursor: pointer; }
        
        /* SETTINGS MODAL */
        .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 2000; opacity: 0; pointer-events: none; transition: 0.3s; display: flex; align-items: flex-end; }
        .modal-overlay.active { opacity: 1; pointer-events: auto; }
        .settings-sheet { background: var(--card); width: 100%; border-radius: 20px 20px 0 0; padding: 25px; transform: translateY(100%); transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 -5px 20px rgba(0,0,0,0.1); padding-bottom: 50px; box-sizing: border-box; }
        .modal-overlay.active .settings-sheet { transform: translateY(0); }
        
        .setting-row { display: flex; justify-content: space-between; align-items: center; padding: 15px 0; border-bottom: 1px solid var(--border); }
        .setting-label { font-weight: 500; font-size: 1rem; }
        .switch { position: relative; display: inline-block; width: 50px; height: 28px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 34px; }
        .slider:before { position: absolute; content: ""; height: 22px; width: 22px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
        input:checked + .slider { background-color: var(--accent); }
        input:checked + .slider:before { transform: translateX(22px); }

        .hidden { display: none !important; }
        .loader { border: 3px solid rgba(128,128,128,0.2); border-top: 3px solid var(--accent); border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 50px auto; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .widget-item-control, .blog-pager { display: none !important; }
    ]]></b:skin>
</head>
<body>

    <div id="loading">
        <div class="loader"></div>
        <p style="text-align:center; color: var(--sub);">Connecting...</p>
    </div>

    <div id="app" class="hidden">
        
        <div class="stats-card">
            <div class="settings-btn" onclick="openSettings()"><i class="fas fa-cog"></i></div>
            <div class="stats-header">
                <div>
                    <h2 style="margin:0; font-size: 1.2rem;">My Cloud</h2>
                    <span style="font-size: 0.8rem; opacity: 0.8;" id="userRole">Standard Plan</span>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 1.5rem; font-weight: 700;" id="storageUsed">0 MB</div>
                    <div style="font-size: 0.7rem; opacity: 0.8;">Used</div>
                </div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size: 0.75rem; margin-bottom: 2px;">
                <span>Storage</span>
                <span id="fileCount">0 Files</span>
            </div>
            <div class="storage-bar"><div class="storage-fill" id="storageFill"></div></div>
        </div>

        <div class="search-box">
            <i class="fas fa-search"></i>
            <input type="text" id="searchInput" placeholder="Search files..." onkeyup="handleSearch()"/>
        </div>

        <h3 style="margin-bottom: 10px; font-size: 0.9rem; color: var(--sub); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Recent Files</h3>
        <ul class="file-list" id="fileList">
            </ul>
        <div id="emptyMsg" style="text-align:center; padding: 40px; color: var(--sub);" class="hidden">
            <i class="fas fa-cloud-upload-alt" style="font-size: 3rem; margin-bottom: 15px; opacity: 0.5;"></i>
            <p>No files found.<br/>Send files to the bot to upload!</p>
        </div>

    </div>

    <div class="modal-overlay" id="settingsModal" onclick="closeSettings(event)">
        <div class="settings-sheet">
            <h2 style="margin-top:0; margin-bottom: 20px;">Settings</h2>
            
            <div class="setting-row">
                <span class="setting-label">Dark Mode</span>
                <label class="switch">
                    <input type="checkbox" id="themeToggle" onchange="toggleTheme()" />
                    <span class="slider"></span>
                </label>
            </div>

            <div class="setting-row">
                <div>
                    <span class="setting-label">TinyURL Shortener</span>
                    <p style="margin:0; font-size:0.8rem; color:var(--sub);">Shorten all download links</p>
                </div>
                <label class="switch">
                    <input type="checkbox" id="shortenerToggle" onchange="toggleShortener()" />
                    <span class="slider"></span>
                </label>
            </div>

            <button onclick="closeSettings()" style="width:100%; padding:15px; background:var(--bg); border:none; border-radius:12px; margin-top:20px; font-weight:bold; color:var(--text); cursor:pointer;">Close</button>
        </div>
    </div>

    <b:section id='main' showaddelement='no'/>

    <script>
    //<![CDATA[
        // ===========================================
        const BASE_URL = "https://tg-file-to-link-bot-tnep.onrender.com"; 
        // ===========================================

        let CURRENT_USER_ID = 0;
        let SEARCH_TIMEOUT = null;
        const tg = window.Telegram.WebApp;

        tg.expand();
        tg.ready();
        tg.setHeaderColor('secondary_bg_color'); 
        tg.setBackgroundColor('bg_color'); 
        tg.enableClosingConfirmation(); 

        function applyTelegramTheme() {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'dark' || tg.colorScheme === 'dark') {
                document.documentElement.classList.add('dark-mode');
                // Check if element exists before setting checked property
                const toggle = document.getElementById('themeToggle');
                if (toggle) toggle.checked = true;
            }
        }
        
        // Call immediately
        applyTelegramTheme();

        async function init() {
            const initData = tg.initData;
            if (!initData) {
                // Browser Login Flow
                document.getElementById('loading').innerHTML = `<div style="text-align:center;padding:40px 20px;"><a id="loginBtn" href="#" target="_blank" style="background:#2481cc;color:white;text-decoration:none;padding:12px 25px;border-radius:10px;font-weight:bold;">Login with Telegram</a></div>`;
                const res = await fetch(`${BASE_URL}/api/auth/generate_token`);
                const data = await res.json();
                document.getElementById('loginBtn').href = data.url;
                const poll = setInterval(async () => {
                    const check = await fetch(`${BASE_URL}/api/auth/check_token?token=${data.token}`);
                    const status = await check.json();
                    if (status.success) { clearInterval(poll); loadApp(status); }
                }, 3000);
                return;
            }

            try {
                const res = await fetch(`${BASE_URL}/api/login`, {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ initData: initData })
                });
                if (!res.ok) throw new Error("Auth Failed");
                loadApp(await res.json());
            } catch (e) { alert("Error: " + e.message); }
        }

        function loadApp(auth) {
            CURRENT_USER_ID = auth.user.id;
            document.getElementById('loading').classList.add('hidden');
            document.getElementById('app').classList.remove('hidden');
            document.getElementById('userRole').innerText = auth.role === 'admin' ? "Admin Access" : "Standard Plan";
            refreshDashboard();
            loadSettings();
        }

        async function refreshDashboard() {
            const res = await fetch(`${BASE_URL}/api/dashboard/user?user_id=${CURRENT_USER_ID}`);
            const data = await res.json();
            const sizeMB = (data.stats.used_storage / 1024 / 1024).toFixed(2);
            document.getElementById('storageUsed').innerText = sizeMB + " MB";
            document.getElementById('fileCount').innerText = data.stats.total_files + " Files";
            document.getElementById('storageFill').style.width = Math.min((data.stats.used_storage / (1024*1024*1024)) * 100, 100) + "%"; 
            renderFiles(data.files);
        }

        function renderFiles(files) {
            const list = document.getElementById('fileList');
            list.innerHTML = "";
            if (!files || files.length === 0) {
                document.getElementById('emptyMsg').classList.remove('hidden'); return;
            }
            document.getElementById('emptyMsg').classList.add('hidden');
            files.forEach(file => {
                const ext = file.file_name.split('.').pop().toLowerCase();
                let icon = 'fa-file';
                if(['mp4','mkv'].includes(ext)) icon='fa-file-video';
                if(['jpg','png'].includes(ext)) icon='fa-file-image';
                
                const li = document.createElement('li');
                li.className = 'file-item';
                li.innerHTML = `
                    <div style="display:flex; align-items:center; flex:1; min-width:0;" onclick="triggerHaptic()">
                        <div class="file-icon"><i class="fas ${icon}"></i></div>
                        <div class="file-info"><h4>${file.file_name}</h4><p>${(file.file_size/1024/1024).toFixed(2)} MB</p></div>
                    </div>
                    <div class="file-actions">
                        <button class="action-btn" onclick="shareFile('${file.link}', '${file.file_name}')"><i class="fas fa-share-alt"></i></button>
                        <button class="action-btn" onclick="renameFile('${file.file_unique_id}', '${file.file_name}')"><i class="fas fa-pen"></i></button>
                        <button class="action-btn delete" onclick="deleteFile('${file.file_unique_id}')"><i class="fas fa-trash"></i></button>
                        <button class="action-btn" style="color:var(--accent)" onclick="downloadFile('${file.link}')"><i class="fas fa-download"></i></button>
                    </div>`;
                list.appendChild(li);
            });
        }

        function openSettings() {
            document.getElementById('settingsModal').classList.add('active');
            triggerHaptic();
        }
        function closeSettings(e) {
            if(!e || e.target.id === 'settingsModal' || !e.target.closest('.settings-sheet')) {
                document.getElementById('settingsModal').classList.remove('active');
            }
        }

        async function loadSettings() {
            try {
                const res = await fetch(`${BASE_URL}/api/settings/get?user_id=${CURRENT_USER_ID}`);
                const data = await res.json();
                const toggle = document.getElementById('shortenerToggle');
                if(toggle) toggle.checked = data.use_shortener;
            } catch(e) {}
        }

        async function toggleShortener() {
            triggerHaptic();
            const val = document.getElementById('shortenerToggle').checked;
            await fetch(`${BASE_URL}/api/settings/update`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: CURRENT_USER_ID, setting: "use_shortener", value: val })
            });
        }

        function toggleTheme() {
            triggerHaptic();
            const isDark = document.getElementById('themeToggle').checked;
            if(isDark) document.documentElement.classList.add('dark-mode');
            else document.documentElement.classList.remove('dark-mode');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        }

        function triggerHaptic() { if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light'); }
        
        function handleSearch() {
            clearTimeout(SEARCH_TIMEOUT);
            SEARCH_TIMEOUT = setTimeout(async () => {
                const query = document.getElementById('searchInput').value;
                if (!query) return refreshDashboard();
                const res = await fetch(`${BASE_URL}/api/search?user_id=${CURRENT_USER_ID}&query=${query}`);
                renderFiles((await res.json()).files);
            }, 500);
        }
        async function renameFile(fid, old) {
            const n = prompt("New name:", old);
            if(n && n!==old) await fetch(`${BASE_URL}/api/file/rename`, {
                method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user_id:CURRENT_USER_ID,file_id:fid,new_name:n})
            }).then(()=>refreshDashboard());
        }
        async function deleteFile(fid) {
            if(confirm("Delete?")) await fetch(`${BASE_URL}/api/file/delete`, {
                method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user_id:CURRENT_USER_ID,file_id:fid})
            }).then(()=>refreshDashboard());
        }
        function downloadFile(link) { tg.initData ? tg.openLink(link,{try_instant_view:false}) : window.open(link,'_blank'); }
        async function shareFile(link, name) {
            if(navigator.share) await navigator.share({title:name,text:'Check this: '+name,url:link});
            else { navigator.clipboard.writeText(link); alert("Copied!"); }
        }

        init();
    //]]>
    </script>
</body>
</html>
