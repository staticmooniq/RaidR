// RaidR — Exact Native Desktop GUI Simulation & Dynamic Theme Engine (60fps Crafted)

const THEMES = {
    'Emerald Green': {
        name: 'Emerald Green',
        primary: '#10B981',
        primaryHov: '#34D399',
        primaryPressed: '#059669',
        primaryDim: 'rgba(16, 185, 129, 0.15)',
        gradTop: '#6EE7B7',
        gradHi: '#34D399',
        gradMid: '#10B981',
        gradLow: '#059669',
        borderGlow: '#A7F3D0',
        onPrimary: '#021B11',
        bgC1: '#0D1714',
        bgC2: '#12211C',
        bgC3: '#0E1915',
        surface: 'rgba(18, 38, 32, 0.70)',
        surfaceHi: 'rgba(25, 52, 44, 0.82)',
        navbar: 'rgba(12, 24, 20, 0.95)',
        text: '#F1F5F9',
        textMuted: '#8FA0B8',
        border: 'rgba(255, 255, 255, 0.08)'
    },
    'Electric Blue': {
        name: 'Electric Blue',
        primary: '#2693FF',
        primaryHov: '#3DA2FF',
        primaryPressed: '#1B7ADB',
        primaryDim: 'rgba(38, 147, 255, 0.15)',
        gradTop: '#5CB5FF',
        gradHi: '#40A6FF',
        gradMid: '#2693FF',
        gradLow: '#147DE8',
        borderGlow: '#75C1FF',
        onPrimary: '#050811',
        bgC1: '#11151C',
        bgC2: '#151A24',
        bgC3: '#121620',
        surface: 'rgba(26, 32, 45, 0.70)',
        surfaceHi: 'rgba(34, 42, 58, 0.82)',
        navbar: 'rgba(18, 22, 31, 0.95)',
        text: '#F1F5F9',
        textMuted: '#8FA0B8',
        border: 'rgba(255, 255, 255, 0.08)'
    },
    'Cyber Purple': {
        name: 'Cyber Purple',
        primary: '#A855F7',
        primaryHov: '#C084FC',
        primaryPressed: '#9333EA',
        primaryDim: 'rgba(168, 85, 247, 0.15)',
        gradTop: '#E9D5FF',
        gradHi: '#C084FC',
        gradMid: '#A855F7',
        gradLow: '#7E22CE',
        borderGlow: '#F3E8FF',
        onPrimary: '#160228',
        bgC1: '#15101F',
        bgC2: '#1D142C',
        bgC3: '#161021',
        surface: 'rgba(38, 25, 56, 0.70)',
        surfaceHi: 'rgba(52, 34, 78, 0.82)',
        navbar: 'rgba(21, 14, 32, 0.95)',
        text: '#F1F5F9',
        textMuted: '#A798C2',
        border: 'rgba(255, 255, 255, 0.08)'
    },
    'Crimson Sunset': {
        name: 'Crimson Sunset',
        primary: '#F43F5E',
        primaryHov: '#FB7185',
        primaryPressed: '#E11D48',
        primaryDim: 'rgba(244, 63, 94, 0.15)',
        gradTop: '#FECDD3',
        gradHi: '#FB7185',
        gradMid: '#F43F5E',
        gradLow: '#BE123C',
        borderGlow: '#FFE4E6',
        onPrimary: '#22040A',
        bgC1: '#1B0F13',
        bgC2: '#26141B',
        bgC3: '#1E1015',
        surface: 'rgba(48, 22, 30, 0.70)',
        surfaceHi: 'rgba(64, 30, 41, 0.82)',
        navbar: 'rgba(26, 12, 17, 0.95)',
        text: '#F1F5F9',
        textMuted: '#BFA2AC',
        border: 'rgba(255, 255, 255, 0.08)'
    },
    'Amber Gold': {
        name: 'Amber Gold',
        primary: '#F59E0B',
        primaryHov: '#FBBF24',
        primaryPressed: '#D97706',
        primaryDim: 'rgba(245, 158, 11, 0.15)',
        gradTop: '#FDE68A',
        gradHi: '#FBBF24',
        gradMid: '#F59E0B',
        gradLow: '#B45309',
        borderGlow: '#FEF3C7',
        onPrimary: '#241401',
        bgC1: '#1A160E',
        bgC2: '#241F13',
        bgC3: '#1C180F',
        surface: 'rgba(44, 36, 20, 0.70)',
        surfaceHi: 'rgba(60, 49, 28, 0.82)',
        navbar: 'rgba(25, 20, 11, 0.95)',
        text: '#F1F5F9',
        textMuted: '#BAAF98',
        border: 'rgba(255, 255, 255, 0.08)'
    },
    'Minimal Monochrome': {
        name: 'Minimal Monochrome',
        primary: '#FFFFFF',
        primaryHov: '#F8FAFC',
        primaryPressed: '#E2E8F0',
        primaryDim: 'rgba(255, 255, 255, 0.15)',
        gradTop: '#FFFFFF',
        gradHi: '#F8FAFC',
        gradMid: '#E2E8F0',
        gradLow: '#94A3B8',
        borderGlow: '#FFFFFF',
        onPrimary: '#0A0A0A',
        bgC1: '#111214',
        bgC2: '#16181B',
        bgC3: '#121316',
        surface: 'rgba(30, 32, 36, 0.70)',
        surfaceHi: 'rgba(42, 45, 52, 0.82)',
        navbar: 'rgba(18, 19, 22, 0.95)',
        text: '#F1F5F9',
        textMuted: '#94A3B8',
        border: 'rgba(255, 255, 255, 0.08)'
    },
    'Pure Pitch Black': {
        name: 'Pure Pitch Black',
        primary: '#38BDF8',
        primaryHov: '#7DD3FC',
        primaryPressed: '#0284C7',
        primaryDim: 'rgba(56, 189, 248, 0.15)',
        gradTop: '#BAE6FD',
        gradHi: '#7DD3FC',
        gradMid: '#38BDF8',
        gradLow: '#0369A1',
        borderGlow: '#E0F2FE',
        onPrimary: '#021019',
        bgC1: '#07080A',
        bgC2: '#0B0D10',
        bgC3: '#08090C',
        surface: 'rgba(18, 20, 26, 0.75)',
        surfaceHi: 'rgba(25, 29, 38, 0.85)',
        navbar: 'rgba(10, 11, 14, 0.95)',
        text: '#F1F5F9',
        textMuted: '#7E8B9E',
        border: 'rgba(255, 255, 255, 0.08)'
    },
    'Deep Midnight Navy': {
        name: 'Deep Midnight Navy',
        primary: '#00D2FF',
        primaryHov: '#33DCFF',
        primaryPressed: '#00A8CC',
        primaryDim: 'rgba(0, 210, 255, 0.15)',
        gradTop: '#80E8FF',
        gradHi: '#33DCFF',
        gradMid: '#00D2FF',
        gradLow: '#007A99',
        borderGlow: '#B3F2FF',
        onPrimary: '#001820',
        bgC1: '#0A121D',
        bgC2: '#0F1A2A',
        bgC3: '#0B131F',
        surface: 'rgba(20, 36, 58, 0.70)',
        surfaceHi: 'rgba(28, 48, 76, 0.82)',
        navbar: 'rgba(12, 20, 32, 0.95)',
        text: '#F1F5F9',
        textMuted: '#8BA1BC',
        border: 'rgba(255, 255, 255, 0.08)'
    }
};

let currentTheme = 'Emerald Green';
let currentVillage = 'home';
let botRunning = false;
let botInterval = null;
let sessionBattles = 0;
let sessionGold = 0;
let sessionElixir = 0;

// Procedural Micro-Audio FX (60fps tactile tick without external audio files)
class SoundFX {
    constructor() {
        this.ctx = null;
    }
    init() {
        if (!this.ctx && (window.AudioContext || window.webkitAudioContext)) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            this.ctx = new AudioCtx();
        }
    }
    tick(freq = 600, duration = 0.03, vol = 0.02) {
        try {
            this.init();
            if (!this.ctx) return;
            if (this.ctx.state === 'suspended') this.ctx.resume();
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
            gain.gain.setValueAtTime(vol, this.ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + duration);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start();
            osc.stop(this.ctx.currentTime + duration);
        } catch (_) {}
    }
    chime() {
        this.tick(520, 0.08, 0.03);
        setTimeout(() => this.tick(780, 0.12, 0.04), 60);
    }
}
const sfx = new SoundFX();

document.addEventListener('DOMContentLoaded', () => {
    initMacOSSmoothScroll();
    initWebsitePaletteSwitcher();
    initThemeEngine();
    initTabNavigation();
    initVillageSwitcher();
    initInteractiveToggles();
    initSliders();
    initSteppers();
    initPillSelections();
    initBotExecutionEngine();
    initWindowControls();
    initLaunchGame();
    initStrategyTroopSwitcher();
    initCocWallEngineReplica();
    initAmbientSpotlight();
    init3DParallaxCards();
    initInfiniteMomentumCarousel();
    initLiveReleaseSync();
});

/* -------------------------------------------------------------
 * 1. THEME ENGINE: Apply 8 Exact Color Schemes
 * ------------------------------------------------------------- */
function initThemeEngine() {
    const root = document.getElementById('virtual-app-root');
    const themeSelect = document.getElementById('app-theme-select');
    const previewLabel = document.getElementById('app-theme-preview');
    const chips = document.querySelectorAll('.theme-chip-btn');

    function applyTheme(name) {
        const theme = THEMES[name];
        if (!theme || !root) return;
        currentTheme = name;

        // Apply CSS custom properties to virtual app
        root.style.setProperty('--app-primary', theme.primary);
        root.style.setProperty('--app-primary-hov', theme.primaryHov);
        root.style.setProperty('--app-primary-pressed', theme.primaryPressed);
        root.style.setProperty('--app-primary-dim', theme.primaryDim);
        root.style.setProperty('--app-grad-top', theme.gradTop);
        root.style.setProperty('--app-grad-hi', theme.gradHi);
        root.style.setProperty('--app-grad-mid', theme.gradMid);
        root.style.setProperty('--app-grad-low', theme.gradLow);
        root.style.setProperty('--app-border-glow', theme.borderGlow);
        root.style.setProperty('--app-on-primary', theme.onPrimary);
        root.style.setProperty('--app-bg-c1', theme.bgC1);
        root.style.setProperty('--app-bg-c2', theme.bgC2);
        root.style.setProperty('--app-bg-c3', theme.bgC3);
        root.style.setProperty('--app-surface', theme.surface);
        root.style.setProperty('--app-surface-hi', theme.surfaceHi);
        root.style.setProperty('--app-navbar', theme.navbar);
        root.style.setProperty('--app-text', theme.text);
        root.style.setProperty('--app-text-muted', theme.textMuted);
        root.style.setProperty('--app-border', theme.border);

        // Update select value & label
        if (themeSelect) themeSelect.value = name;
        if (previewLabel) previewLabel.textContent = `${name} Active`;

        // Update active chip
        chips.forEach(chip => {
            if (chip.getAttribute('data-theme') === name) {
                chip.classList.add('active');
            } else {
                chip.classList.remove('active');
            }
        });

        // Re-color sliders
        document.querySelectorAll('.app-themed-slider').forEach(slider => {
            const val = parseInt(slider.value);
            const min = parseInt(slider.min) || 1;
            const max = parseInt(slider.max) || 15;
            const pct = ((val - min) / (max - min)) * 100;
            slider.style.setProperty('--slider-pct', `${pct}%`);
        });

        sfx.tick(700, 0.05);
    }

    if (themeSelect) {
        themeSelect.addEventListener('change', (e) => applyTheme(e.target.value));
    }

    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            const themeName = chip.getAttribute('data-theme');
            applyTheme(themeName);
        });
    });

    // Default to Emerald Green (matches screenshot)
    applyTheme('Emerald Green');
}

/* -------------------------------------------------------------
 * 2. TOP TABS: Run | Settings | Logs
 * ------------------------------------------------------------- */
function initTabNavigation() {
    const tabs = document.querySelectorAll('.app-nav-tab');
    const pages = document.querySelectorAll('.app-page-view');
    const runDock = document.getElementById('app-run-dock');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const pageName = tab.getAttribute('data-page');
            const pageId = `page-${pageName}`;

            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            pages.forEach(p => {
                if (p.id === pageId) {
                    p.classList.remove('hidden');
                } else {
                    p.classList.add('hidden');
                }
            });

            // Show pinned Run Action Bar only on Run page
            if (runDock) {
                if (pageName === 'run') {
                    runDock.classList.remove('hidden');
                } else {
                    runDock.classList.add('hidden');
                }
            }

            sfx.tick(540, 0.03);
        });
    });
}

/* -------------------------------------------------------------
 * 3. VILLAGE SWITCHER: Home Village vs Builder Base
 * ------------------------------------------------------------- */
function initVillageSwitcher() {
    const btnHV = document.getElementById('navbar-village-hv');
    const btnBB = document.getElementById('navbar-village-bb');
    const hvCards = document.querySelectorAll('.village-hv-only');
    const bbCards = document.querySelectorAll('.village-bb-only');
    const footerStatus = document.getElementById('app-footer-state-text');

    function switchVillage(v) {
        currentVillage = v;
        if (v === 'home') {
            btnHV.classList.add('active');
            btnBB.classList.remove('active');
            hvCards.forEach(c => c.classList.remove('hidden'));
            bbCards.forEach(c => c.classList.add('hidden'));
            if (!botRunning && footerStatus) {
                footerStatus.textContent = 'Ready (Home Village)';
            }
        } else {
            btnBB.classList.add('active');
            btnHV.classList.remove('active');
            bbCards.forEach(c => c.classList.remove('hidden'));
            hvCards.forEach(c => c.classList.add('hidden'));
            if (!botRunning && footerStatus) {
                footerStatus.textContent = 'Ready (Builder Base)';
            }
        }
        sfx.tick(640, 0.04);
    }

    if (btnHV) {
        btnHV.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            switchVillage('home');
        });
    }

    if (btnBB) {
        btnBB.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            switchVillage('builder');
        });
    }
}

/* -------------------------------------------------------------
 * 4. INTERACTIVE TOGGLE SWITCHES
 * ------------------------------------------------------------- */
function initInteractiveToggles() {
    const toggles = document.querySelectorAll('.app-toggle');

    toggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const isActive = toggle.classList.toggle('active');
            sfx.tick(isActive ? 720 : 480, 0.03);
        });
    });
}

/* -------------------------------------------------------------
 * 5. FREQUENCY SLIDERS (Home Village & Builder Base)
 * ------------------------------------------------------------- */
function initSliders() {
    const sliders = [
        { slider: document.getElementById('hv-wall-slider'), badge: document.getElementById('hv-wall-badge') },
        { slider: document.getElementById('bb-wall-slider'), badge: document.getElementById('bb-wall-badge') }
    ];

    sliders.forEach(({ slider, badge }) => {
        if (!slider) return;

        function update(val) {
            const min = parseInt(slider.min) || 1;
            const max = parseInt(slider.max) || 15;
            const pct = ((val - min) / (max - min)) * 100;
            slider.style.setProperty('--slider-pct', `${pct}%`);
            if (badge) {
                badge.textContent = val === 1 ? 'Every 1 battle' : `Every ${val} battles`;
            }
        }

        slider.addEventListener('input', (e) => {
            update(parseInt(e.target.value));
            sfx.tick(500 + parseInt(e.target.value) * 20, 0.015, 0.01);
        });
        update(parseInt(slider.value) || 3);
    });
}

/* -------------------------------------------------------------
 * 6. DURATION STEPPER & QUICK PRESETS
 * ------------------------------------------------------------- */
function initSteppers() {
    const durInput = document.getElementById('app-duration-input');
    const stepUp = document.getElementById('app-duration-up');
    const stepDown = document.getElementById('app-duration-down');
    const pills = document.querySelectorAll('.app-duration-pill');

    function setDuration(val) {
        const clamped = Math.max(1, Math.min(999, parseInt(val) || 120));
        if (durInput) durInput.value = clamped;
        sfx.tick(580, 0.025);
    }

    if (stepUp) {
        stepUp.addEventListener('click', () => {
            setDuration(parseInt(durInput.value) + 5);
        });
    }

    if (stepDown) {
        stepDown.addEventListener('click', () => {
            setDuration(parseInt(durInput.value) - 5);
        });
    }

    pills.forEach(pill => {
        pill.addEventListener('click', () => {
            const minutes = parseInt(pill.getAttribute('data-min'));
            setDuration(minutes);
        });
    });
}

/* -------------------------------------------------------------
 * 7. PILL BUTTONS (Attack Strategy & Modes Radios)
 * ------------------------------------------------------------- */
function initPillSelections() {
    const modeGroups = document.querySelectorAll('.app-radio-group');
    modeGroups.forEach(group => {
        const buttons = group.querySelectorAll('.app-radio-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                buttons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                sfx.tick(620, 0.03);
            });
        });
    });

    const strategyBtns = document.querySelectorAll('.app-strategy-select-btn');
    strategyBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            strategyBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            sfx.tick(660, 0.03);
        });
    });
}

/* -------------------------------------------------------------
 * 8. STRATEGY TROOP SWITCHER & DROPDOWN (HOME VILLAGE & BUILDER BASE)
 * ------------------------------------------------------------- */
function initStrategyTroopSwitcher() {
    // 1. Home Village Strategy Dropdown (Matching Screenshot)
    const hvDropBtn = document.getElementById('hv-strat-dropdown-btn');
    const hvDropMenu = document.getElementById('hv-strat-menu');
    const hvStratName = document.getElementById('hv-strat-name');
    const hvTroopImg = document.getElementById('hv-troop-img');
    const hvTroopText = document.getElementById('hv-troop-text');

    if (hvDropBtn && hvDropMenu) {
        hvDropBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            hvDropMenu.classList.toggle('hidden');
            sfx.tick(680, 0.03);
        });

        const menuItems = hvDropMenu.querySelectorAll('.hv-strat-menu-item');
        menuItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                menuItems.forEach(i => i.classList.remove('active'));
                item.classList.add('active');

                const stratName = item.getAttribute('data-strategy');
                const troopName = item.getAttribute('data-name');
                const count = item.getAttribute('data-count');
                const troopKey = item.getAttribute('data-troop');

                if (hvStratName) hvStratName.textContent = stratName;
                if (hvTroopText) {
                    hvTroopText.innerHTML = `${troopName} <span class="text-white">${count}</span>`;
                }

                if (hvTroopImg) {
                    if (troopKey === 'edrag') {
                        hvTroopImg.src = 'assets/edrag.png';
                    } else {
                        hvTroopImg.src = 'assets/default_troop_placeholder.png';
                    }
                }

                hvDropMenu.classList.add('hidden');
                sfx.tick(740, 0.04);
            });
        });

        document.addEventListener('click', (e) => {
            if (!hvDropBtn.contains(e.target) && !hvDropMenu.contains(e.target)) {
                hvDropMenu.classList.add('hidden');
            }
        });
    }

    // 2. Builder Base Strategy Buttons
    const btnBaby = document.getElementById('bb-strat-babydragon');
    const btnWitch = document.getElementById('bb-strat-nightwitch');
    const troopImg = document.getElementById('bb-troop-img');
    const troopText = document.getElementById('bb-troop-text');

    if (btnBaby && btnWitch && troopImg && troopText) {
        btnBaby.addEventListener('click', () => {
            btnBaby.classList.add('active');
            btnWitch.classList.remove('active');
            troopImg.src = 'assets/babydragon.png';
            troopText.innerHTML = `Baby Dragon <span class="text-white">x6</span>`;
            troopText.className = 'text-xs font-mono font-bold text-emerald-300';
            sfx.tick(740, 0.04);
        });

        btnWitch.addEventListener('click', () => {
            btnWitch.classList.add('active');
            btnBaby.classList.remove('active');
            troopImg.src = 'assets/nightwitch.png';
            troopText.innerHTML = `Night Witch <span class="text-white">x6</span>`;
            troopText.className = 'text-xs font-mono font-bold text-purple-300';
            sfx.tick(740, 0.04);
        });
    }
}

/* -------------------------------------------------------------
 * 9. BOT SIMULATION ENGINE (Start / Stop & Real-Time Logs)
 * ------------------------------------------------------------- */
function initBotExecutionEngine() {
    const startBtn = document.getElementById('app-start-btn');
    const stopBtn = document.getElementById('app-stop-btn');
    const footerStatus = document.getElementById('app-footer-state-text');
    const liveState = document.getElementById('live-metric-state');
    const liveLoot = document.getElementById('live-metric-loot');
    const liveRate = document.getElementById('live-metric-rate');
    const logsBox = document.getElementById('app-terminal-logs');
    const clearLogsBtn = document.getElementById('app-clear-logs-btn');

    function appendLog(level, msg) {
        if (!logsBox) return;
        const now = new Date();
        const ts = now.toISOString().replace('T', ' ').substring(0, 19);
        const line = document.createElement('div');
        line.innerHTML = `<span class="log-time">${ts}</span> - <span class="log-src">BotController</span> - <span class="log-level">${level}</span> - <span class="log-msg">${msg}</span>`;
        logsBox.appendChild(line);
        logsBox.scrollTop = logsBox.scrollHeight;
    }

    if (startBtn && stopBtn) {
        startBtn.addEventListener('click', () => {
            if (botRunning) return;
            botRunning = true;

            startBtn.classList.add('opacity-90');
            startBtn.innerHTML = `<span class="animate-pulse">●</span><span>Bot Running...</span>`;
            stopBtn.classList.add('enabled');

            const vName = currentVillage === 'home' ? 'Home Village' : 'Builder Base';
            if (footerStatus) footerStatus.textContent = `Running: Farming ${vName}...`;
            if (liveState) liveState.textContent = 'Searching target...';

            appendLog('INFO', `Starting bot loop on ${vName}`);
            appendLog('INFO', `Aspect configuration: 16:9 profile (2560x1440 ref)`);
            appendLog('INFO', `Attached to Clash of Clans (Google Play Games PC)`);

            sfx.chime();

            botInterval = setInterval(() => {
                sessionBattles += 1;
                const earnedGold = Math.floor(Math.random() * 300000) + 450000;
                const earnedElixir = Math.floor(Math.random() * 280000) + 420000;
                sessionGold += earnedGold;
                sessionElixir += earnedElixir;

                if (liveState) {
                    const states = currentVillage === 'home' 
                        ? ['Farming dead base', 'Deploying Electro Dragons', 'Inspecting wall rows', 'Checking upgrades']
                        : ['Attacking Stage 1', 'Night Witches deployed', 'Transitioning to Stage 2', 'Upgrading BB walls'];
                    liveState.textContent = states[sessionBattles % states.length];
                }

                if (liveLoot) {
                    const gM = (sessionGold / 1000000).toFixed(2);
                    const eM = (sessionElixir / 1000000).toFixed(2);
                    liveLoot.textContent = `+${gM}M Gold / +${eM}M Elixir`;
                }

                if (liveRate) {
                    liveRate.textContent = `1.35M / hr`;
                }

                if (sessionBattles % 2 === 1) {
                    const stars = currentVillage === 'home' ? '3 Stars' : '200% (6 Stars)';
                    appendLog('INFO', `Raid finished: ${stars}! Loot gained: +${Math.round(earnedGold/1000)}k Gold, +${Math.round(earnedElixir/1000)}k Elixir`);
                } else {
                    const walls = Math.floor(Math.random() * 8) + 4;
                    const res = sessionBattles % 4 === 0 ? 'Elixir' : 'Gold';
                    appendLog('INFO', `Multi-wall check: Found affordable batch of ${walls} walls. Upgrading with ${res}!`);
                }
            }, 3500);
        });

        stopBtn.addEventListener('click', () => {
            if (!botRunning) return;
            botRunning = false;
            clearInterval(botInterval);

            startBtn.classList.remove('opacity-90');
            startBtn.innerHTML = `<span class="app-btn-start-icon text-xs">▶</span><span>Start bot</span>`;
            stopBtn.classList.remove('enabled');

            const vName = currentVillage === 'home' ? 'Home Village' : 'Builder Base';
            if (footerStatus) footerStatus.textContent = `Ready (${vName})`;
            if (liveState) liveState.textContent = 'Ready';

            appendLog('WARNING', 'Bot execution halted by user.');
            sfx.tick(400, 0.08);
        });
    }

    if (clearLogsBtn && logsBox) {
        clearLogsBtn.addEventListener('click', () => {
            logsBox.innerHTML = '<div class="text-slate-500 italic">Logs cleared. Ready for next session...</div>';
            sfx.tick(500, 0.03);
        });
    }
}

/* -------------------------------------------------------------
 * 10. DESKTOP WINDOW SIMULATION CONTROLS (Min, Max, Close)
 * ------------------------------------------------------------- */
function initWindowControls() {
    const root = document.getElementById('virtual-app-root');
    const btnMin = document.getElementById('btn-win-min');
    const btnMax = document.getElementById('btn-win-max');
    const btnClose = document.getElementById('btn-win-close');
    const dock = document.getElementById('minimized-taskbar-dock');
    const toast = document.getElementById('app-toast');
    const toastMsg = document.getElementById('app-toast-msg');

    function showToast(msg, duration = 2800) {
        if (!toast || !toastMsg) return;
        toastMsg.textContent = msg;
        toast.classList.remove('hidden');
        setTimeout(() => toast.classList.add('hidden'), duration);
    }

    if (btnMin && root && dock) {
        btnMin.addEventListener('click', () => {
            root.classList.add('is-minimized');
            dock.classList.remove('hidden');
            sfx.tick(450, 0.06);
        });

        dock.addEventListener('click', () => {
            root.classList.remove('is-minimized');
            dock.classList.add('hidden');
            sfx.tick(650, 0.06);
        });
    }

    if (btnMax && root) {
        btnMax.addEventListener('click', () => {
            const isMax = root.classList.toggle('is-maximized');
            sfx.tick(isMax ? 750 : 550, 0.04);
        });
    }

    if (btnClose) {
        btnClose.addEventListener('click', () => {
            showToast('RaidR minimized to system tray. Background automation stays active.');
            sfx.tick(420, 0.05);
        });
    }
}

/* -------------------------------------------------------------
 * 11. LAUNCH GAME SIMULATION
 * ------------------------------------------------------------- */
function initLaunchGame() {
    const launchBtn = document.getElementById('btn-launch-game');
    const toast = document.getElementById('app-toast');
    const toastMsg = document.getElementById('app-toast-msg');
    const logsBox = document.getElementById('app-terminal-logs');

    if (launchBtn) {
        launchBtn.addEventListener('click', () => {
            if (toast && toastMsg) {
                toastMsg.textContent = '🎮 Hooked Clash of Clans via Google Play Games PC (Window: CROSVM, 2560x1440).';
                toast.classList.remove('hidden');
                setTimeout(() => toast.classList.add('hidden'), 3500);
            }

            if (logsBox) {
                const now = new Date();
                const ts = now.toISOString().replace('T', ' ').substring(0, 19);
                const line = document.createElement('div');
                line.innerHTML = `<span class="log-time">${ts}</span> - <span class="log-src">WindowService</span> - <span class="log-level">INFO</span> - <span class="log-msg">DirectX surface attached: Google Play Games PC (Clash of Clans)</span>`;
                logsBox.appendChild(line);
                logsBox.scrollTop = logsBox.scrollHeight;
            }

            sfx.chime();
        });
    }
}

/* -------------------------------------------------------------
 * 12. CLASH OF CLANS IN-GAME MULTI-WALL REPLICA HUD
 * ------------------------------------------------------------- */
function initCocWallEngineReplica() {
    const countLabel = document.getElementById('coc-selected-walls');
    if (!countLabel) return;

    let wallCount = 10;
    const baseCostPerWall = 960000;
    const priceGold = document.getElementById('coc-price-gold');
    const priceElixir = document.getElementById('coc-price-elixir');
    const statusText = document.getElementById('coc-wall-status');
    const toast = document.getElementById('coc-upgrade-toast');
    const toastText = document.getElementById('coc-upgrade-toast-text');

    const btnSub1 = document.getElementById('coc-btn-sub1');
    const btnAdd1 = document.getElementById('coc-btn-add1');
    const btnAdd10 = document.getElementById('coc-btn-add10');
    const btnGold = document.getElementById('coc-btn-gold');
    const btnElixir = document.getElementById('coc-btn-elixir');

    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    }

    function renderWalls() {
        if (countLabel) countLabel.textContent = `${wallCount} Walls`;
        const totalCost = wallCount * baseCostPerWall;
        const formatted = formatNumber(totalCost);
        if (priceGold) priceGold.textContent = formatted;
        if (priceElixir) priceElixir.textContent = formatted;
        if (statusText) statusText.textContent = `Batch Cost: ${formatted}`;
    }

    function updateCount(delta) {
        wallCount = Math.max(1, Math.min(25, wallCount + delta));
        renderWalls();
        sfx.tick(550 + wallCount * 15, 0.02);
    }

    if (btnSub1) btnSub1.addEventListener('click', () => updateCount(-1));
    if (btnAdd1) btnAdd1.addEventListener('click', () => updateCount(1));
    if (btnAdd10) btnAdd10.addEventListener('click', () => updateCount(10));

    function triggerUpgrade(resource) {
        const totalCost = wallCount * baseCostPerWall;
        const formatted = formatNumber(totalCost);
        if (toast && toastText) {
            toastText.innerHTML = `Upgraded <strong>${wallCount} walls</strong> for <strong>${formatted} ${resource}</strong>! Zero gems spent.`;
            toast.classList.remove('hidden');
            setTimeout(() => toast.classList.add('hidden'), 3500);
        }
        if (statusText) {
            statusText.textContent = `Upgraded with ${resource}!`;
        }
        sfx.chime();
    }

    if (btnGold) btnGold.addEventListener('click', () => triggerUpgrade('Gold'));
    if (btnElixir) btnElixir.addEventListener('click', () => triggerUpgrade('Elixir'));

    renderWalls();
}

/* -------------------------------------------------------------
 * 13. AMBIENT MOUSE SPOTLIGHT (60FPS ACCELERATED)
 * ------------------------------------------------------------- */
function initAmbientSpotlight() {
    const spotlight = document.getElementById('ambient-spotlight');
    if (!spotlight) return;

    let targetX = window.innerWidth / 2;
    let targetY = window.innerHeight / 2;
    let currentX = targetX;
    let currentY = targetY;

    window.addEventListener('mousemove', (e) => {
        targetX = e.clientX;
        targetY = e.clientY;
    }, { passive: true });

    function render() {
        currentX += (targetX - currentX) * 0.12;
        currentY += (targetY - currentY) * 0.12;
        spotlight.style.transform = `translate3d(${currentX}px, ${currentY}px, 0) translate(-50%, -50%)`;
        requestAnimationFrame(render);
    }
    requestAnimationFrame(render);
}

/* -------------------------------------------------------------
 * 14. 3D PARALLAX REACTIVE CARDS (60FPS INTERACTION)
 * ------------------------------------------------------------- */
function init3DParallaxCards() {
    const cards = document.querySelectorAll('.parallax-card-3d');
    if (!cards.length) return;

    cards.forEach(card => {
        let isHovered = false;

        card.addEventListener('mouseenter', () => {
            isHovered = true;
            card.style.animation = 'none'; // pause idle float on active interaction
        });

        card.addEventListener('mousemove', (e) => {
            if (!isHovered || card.closest('.is-dragging')) return;
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            // Set mouse spotlight position in CSS vars
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);

            // Compute tilt angles (-11deg to +11deg)
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const tiltX = -((y - centerY) / centerY) * 11;
            const tiltY = ((x - centerX) / centerX) * 11;

            card.style.transform = `perspective(1000px) rotateX(${tiltX.toFixed(2)}deg) rotateY(${tiltY.toFixed(2)}deg) scale3d(1.025, 1.025, 1.025)`;
        });

        card.addEventListener('mouseleave', () => {
            isHovered = false;
            card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
            setTimeout(() => {
                if (!isHovered) {
                    card.style.animation = ''; // resume idle float
                }
            }, 300);
        });
    });
}

/* -------------------------------------------------------------
 * 15. INFINITE MOMENTUM CAROUSEL STRIP (DRAG & FLICK 60FPS)
 * ------------------------------------------------------------- */
function initInfiniteMomentumCarousel() {
    const viewport = document.getElementById('features-carousel-viewport');
    const track = document.getElementById('features-carousel-track');
    if (!viewport || !track) return;

    const BASE_SPEED = -0.75; // Slow continuous auto-scroll (px/frame)
    let posX = 0;
    let velocity = BASE_SPEED;
    let isDragging = false;
    let startX = 0;
    let lastX = 0;
    let lastTime = 0;
    let velocitySamples = [];
    let halfWidth = 0;
    let hasMoved = false;

    function computeDimensions() {
        // Track holds 2 identical sets of 6 cards. halfWidth is the exact wrap boundary.
        halfWidth = track.scrollWidth / 2;
    }
    computeDimensions();
    window.addEventListener('resize', computeDimensions, { passive: true });
    setTimeout(computeDimensions, 500);
    setTimeout(computeDimensions, 1500);

    // Pointer Events for Drag & Flick
    viewport.addEventListener('pointerdown', (e) => {
        if (e.button !== 0) return; // Only primary button
        isDragging = true;
        hasMoved = false;
        viewport.classList.add('is-dragging');
        try {
            viewport.setPointerCapture(e.pointerId);
        } catch (_) {}

        startX = e.clientX;
        lastX = e.clientX;
        lastTime = performance.now();
        velocitySamples = [];
        velocity = 0;
    });

    viewport.addEventListener('pointermove', (e) => {
        if (!isDragging) return;
        const now = performance.now();
        const clientX = e.clientX;
        const dx = clientX - lastX;
        const dt = now - lastTime;

        if (Math.abs(clientX - startX) > 3) {
            hasMoved = true;
        }

        if (dt > 0) {
            velocitySamples.push({ dx, dt, time: now });
            velocitySamples = velocitySamples.filter(s => now - s.time < 90);
        }

        posX += dx;

        // Wrap around boundary check
        if (halfWidth > 0) {
            while (posX <= -halfWidth) posX += halfWidth;
            while (posX > 0) posX -= halfWidth;
        }

        track.style.transform = `translate3d(${posX.toFixed(2)}px, 0, 0)`;

        lastX = clientX;
        lastTime = now;
    });

    function endDrag(e) {
        if (!isDragging) return;
        isDragging = false;
        viewport.classList.remove('is-dragging');
        try {
            viewport.releasePointerCapture(e.pointerId);
        } catch (_) {}

        const now = performance.now();
        const recentSamples = velocitySamples.filter(s => now - s.time < 100);

        if (recentSamples.length > 0) {
            let totalDx = 0;
            let totalDt = 0;
            recentSamples.forEach(s => {
                totalDx += s.dx;
                totalDt += s.dt;
            });
            if (totalDt > 0) {
                const measuredVel = (totalDx / totalDt) * 16.67;
                const MAX_FLICK = 35;
                velocity = Math.max(-MAX_FLICK, Math.min(MAX_FLICK, measuredVel));
            }
        }

        if (Math.abs(velocity) < 0.2) {
            velocity = BASE_SPEED;
        }
    }

    viewport.addEventListener('pointerup', endDrag);
    viewport.addEventListener('pointercancel', endDrag);

    // Prevent click on cards when dragged/flicked
    viewport.addEventListener('click', (e) => {
        if (hasMoved) {
            e.preventDefault();
            e.stopPropagation();
        }
    }, true);

    // Animation Loop (60fps requestAnimationFrame)
    function animate() {
        if (!isDragging) {
            // Apply exponential momentum decay toward BASE_SPEED
            if (Math.abs(velocity - BASE_SPEED) > 0.02) {
                velocity = velocity * 0.94 + BASE_SPEED * 0.06;
            } else {
                velocity = BASE_SPEED;
            }

            posX += velocity;

            // Seamless infinite wrap
            if (halfWidth > 0) {
                while (posX <= -halfWidth) posX += halfWidth;
                while (posX > 0) posX -= halfWidth;
            }

            track.style.transform = `translate3d(${posX.toFixed(2)}px, 0, 0)`;
        }

        requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
}

/* -------------------------------------------------------------
 * 16. LIVE GITHUB RELEASE AUTO-SYNC
 * ------------------------------------------------------------- */
async function initLiveReleaseSync() {
    const versionElements = document.querySelectorAll('.live-release-version');
    const downloadButtons = document.querySelectorAll('.live-download-btn');
    const downloadLabels = document.querySelectorAll('.live-download-label');

    try {
        const res = await fetch('https://api.github.com/repos/staticmooniq/RaidR/releases/latest', {
            headers: { 'Accept': 'application/vnd.github.v3+json' }
        });
        if (!res.ok) return;

        const data = await res.json();
        const rawTag = data.tag_name || '1.3.0';
        const displayTag = rawTag.startsWith('v') ? rawTag : `v${rawTag}`;

        let downloadUrl = data.html_url;
        if (Array.isArray(data.assets)) {
            const exeAsset = data.assets.find(a => a.name && a.name.toLowerCase().endsWith('.exe'));
            if (exeAsset && exeAsset.browser_download_url) {
                downloadUrl = exeAsset.browser_download_url;
            }
        }

        versionElements.forEach(el => {
            el.textContent = displayTag;
        });

        downloadButtons.forEach(btn => {
            btn.href = downloadUrl;
        });

        downloadLabels.forEach(lbl => {
            lbl.textContent = `Download RaidR ${displayTag} (.exe)`;
        });

        console.log(`[RaidR Live Sync] Synchronized with GitHub Release ${displayTag} -> ${downloadUrl}`);
    } catch (err) {
        console.log('[RaidR Live Sync] Using baked v1.3 defaults', err);
    }
}

/* -------------------------------------------------------------
 * 17. LIVE WEBSITE PALETTE SWITCHER
 * ------------------------------------------------------------- */
function initWebsitePaletteSwitcher() {
    const dots = document.querySelectorAll('.web-theme-dot');
    if (!dots.length) return;

    function applyPalette(themeName) {
        if (!themeName) return;
        document.documentElement.setAttribute('data-theme-palette', themeName);
        localStorage.setItem('raidr_web_palette', themeName);

        dots.forEach(dot => {
            if (dot.getAttribute('data-web-theme') === themeName) {
                dot.classList.add('active');
            } else {
                dot.classList.remove('active');
            }
        });

        sfx.tick(680, 0.04);
    }

    dots.forEach(dot => {
        dot.addEventListener('click', () => {
            const theme = dot.getAttribute('data-web-theme');
            applyPalette(theme);
        });
    });

    const saved = localStorage.getItem('raidr_web_palette');
    applyPalette(saved || 'emerald-matrix');
}

/* -------------------------------------------------------------
 * 18. MACOS-STYLE BUTTERY MOMENTUM SMOOTH SCROLL (LENIS ENGINE)
 * ------------------------------------------------------------- */
function initMacOSSmoothScroll() {
    if (typeof Lenis === 'undefined') return;

    let lastWheelDeltaY = 0;
    window.addEventListener('wheel', (e) => {
        lastWheelDeltaY = e.deltaY;
    }, { capture: true, passive: true });

    const lenis = new Lenis({
        duration: 1.25, // Apple-style smooth deceleration window
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)), // Exponential momentum curve
        direction: 'vertical',
        gestureDirection: 'vertical',
        smooth: true,
        mouseMultiplier: 0.95, // Butter smooth mouse wheel scaling
        smoothTouch: false,    // Preserve native 120Hz touch physics on mobile/tablets
        touchMultiplier: 1.5,
        infinite: false,
        prevent: (node) => {
            // Find if mouse event originated inside a scrollable container within the virtual app
            const vp = node.closest('.app-viewport, .app-logs-terminal');
            if (!vp) return false;

            const maxScroll = vp.scrollHeight - vp.clientHeight;
            // If the container has no scrollable overflow, immediately allow Lenis to scroll the website
            if (maxScroll <= 2) return false;

            const isAtTop = vp.scrollTop <= 2;
            const isAtBottom = vp.scrollTop >= maxScroll - 2;

            // When scrolling down and already at the bottom of the simulation window:
            // Do NOT prevent -> pass through to Lenis to smoothly scroll the website!
            if (lastWheelDeltaY > 0 && isAtBottom) {
                return false;
            }

            // When scrolling up and already at the top of the simulation window:
            // Do NOT prevent -> pass through to Lenis to smoothly scroll the website!
            if (lastWheelDeltaY < 0 && isAtTop) {
                return false;
            }

            // Still has scrollable content in the wheel direction -> let the simulation window scroll natively
            return true;
        }
    });

    function raf(time) {
        lenis.raf(time);
        requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);

    // Intercept all in-page hash anchor links (e.g. #simulator, #features, #download)
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
            const href = anchor.getAttribute('href');
            if (href === '#' || !href) return;
            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                lenis.scrollTo(target, {
                    offset: -40,
                    duration: 1.3,
                    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t))
                });
            }
        });
    });

    window.lenis = lenis;
}
