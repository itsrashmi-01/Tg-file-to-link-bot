<script>
    //<![CDATA[
        const BASE_URL = "https://tg-file-to-link-bot-tnep.onrender.com"; 
        
        let CURRENT_USER_ID = 0;
        const tg = window.Telegram.WebApp;

        tg.expand();
        tg.ready();
        tg.setHeaderColor('secondary_bg_color'); 
        tg.setBackgroundColor('bg_color'); 
        tg.enableClosingConfirmation(); 

        function applyTelegramTheme() {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'dark' || (!savedTheme && tg.colorScheme === 'dark')) {
                document.documentElement.classList.add('dark-mode');
                syncToggles(true);
            } else {
                syncToggles(false);
            }
        }
        
        function syncToggles(isDark) {
            const t1 = document.getElementById('themeToggleSettings');
            const t2 = document.getElementById('themeToggleProfile');
            if(t1) t1.checked = isDark;
            if(t2) t2.checked = isDark;
        }
        
        applyTelegramTheme();

        async function init() {
            const initData = tg.initData;
            
            // --- 1. EXTRACT BOT ID FROM URL ---
            const urlParams = new URLSearchParams(window.location.search);
            const botId = urlParams.get('bot_id') || ""; 
            // ----------------------------------

            if (!initData) {
                // Browser Login (Manual)
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
                // --- 2. SEND BOT ID IN LOGIN ---
                const res = await fetch(`${BASE_URL}/api/login`, {
                    method: "POST", 
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ 
                        initData: initData,
                        bot_id: botId // <--- Sending this allows backend to pick correct token
                    })
                });
                // -------------------------------
                
                if (!res.ok) throw new Error("Auth Failed");
                loadApp(await res.json());
            } catch (e) { alert("Error: " + e.message); }
        }

        // ... (Keep the rest of loadApp, refreshDashboard, etc. exactly as they were in previous steps)
        function loadApp(auth) {
            CURRENT_USER_ID = auth.user.id;
            document.getElementById('loading').classList.add('hidden');
            document.getElementById('app').classList.remove('hidden');
            document.getElementById('userRole').innerText = auth.role === 'admin' ? "Admin Access" : "Standard Plan";
            document.getElementById('profileName').innerText = auth.user.first_name || "User";
            document.getElementById('userIdDisplay').innerText = auth.user.id;
            refreshDashboard();
            loadSettings();
        }
        
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            document.getElementById('nav-' + tabId).classList.add('active');
            triggerHaptic();
        }
        
        async function refreshDashboard() {
            const res = await fetch(`${BASE_URL}/api/dashboard/user?user_id=${CURRENT_USER_ID}`);
            const data = await res.json();
            
            const sizeMB = (data.stats.used_storage / 1024 / 1024).toFixed(2);
            document.getElementById('storageUsed').innerText = sizeMB + " MB";
            document.getElementById('fileCount').innerText = data.stats.total_files + " Files";
            document.getElementById('storageFill').style.width = Math.min((data.stats.used_storage / (1024*1024*1024)) * 100, 100) + "%"; 
            
            if (data.clone_bot) {
                document.getElementById('cloneCard').classList.remove('hidden');
                document.getElementById('cloneUsername').innerText = "@" + data.clone_bot.username;
                document.getElementById('cloneLink').href = "https://t.me/" + data.clone_bot.username;
                document.getElementById('cloneSettingsSection').classList.remove('hidden');
            } else {
                document.getElementById('cloneCard').classList.add('hidden');
                document.getElementById('cloneSettingsSection').classList.add('hidden');
            }

            renderFiles(data.files.slice(0, 5), 'fileList', 'emptyMsg');
            renderFiles(data.files, 'allFileList', 'emptyMsgAll');
        }
        
        async function editClone() {
            if(confirm("Manage Clone Bot:\n\nDo you want to DELETE this clone? This cannot be undone.")) {
                await fetch(`${BASE_URL}/api/clone/delete`, {
                    method: "POST", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({user_id: CURRENT_USER_ID})
                });
                refreshDashboard();
            }
        }

        function renderFiles(files, listId, emptyId) {
            const list = document.getElementById(listId);
            list.innerHTML = "";
            if (!files || files.length === 0) {
                document.getElementById(emptyId).classList.remove('hidden'); return;
            }
            document.getElementById(emptyId).classList.add('hidden');
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

        function toggleTheme(event) {
            triggerHaptic();
            const isDark = event.target.checked;
            syncToggles(isDark);
            if (document.startViewTransition) {
                const x = event.clientX;
                const y = event.clientY;
                const endRadius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
                const transition = document.startViewTransition(() => {
                    if (isDark) document.documentElement.classList.add('dark-mode');
                    else document.documentElement.classList.remove('dark-mode');
                });
                transition.ready.then(() => {
                    const clipPath = [`circle(0px at ${x}px ${y}px)`, `circle(${endRadius}px at ${x}px ${y}px)`];
                    document.documentElement.animate(
                        { clipPath: clipPath },
                        { duration: 500, easing: 'ease-in-out', pseudoElement: '::view-transition-new(root)' }
                    );
                });
            } else {
                if (isDark) document.documentElement.classList.add('dark-mode');
                else document.documentElement.classList.remove('dark-mode');
            }
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        }

        function triggerHaptic() { if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light'); }
        
        function handleSearch() {
            clearTimeout(SEARCH_TIMEOUT);
            SEARCH_TIMEOUT = setTimeout(async () => {
                const query = document.getElementById('allSearchInput').value;
                if (!query) return refreshDashboard();
                const res = await fetch(`${BASE_URL}/api/search?user_id=${CURRENT_USER_ID}&query=${query}`);
                renderFiles((await res.json()).files, 'allFileList', 'emptyMsgAll');
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
