"""RaidR — Dark Neumorphic & Theme Templates."""
from __future__ import annotations
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

THEME_TEMPLATES = {
    'Electric Blue': {
        'name': 'Electric Blue',
        'primary': '#2693FF',
        'primary_hov': '#3DA2FF',
        'primary_pressed': '#1B7ADB',
        'primary_dim': 'rgba(38, 147, 255, 0.15)',
        'grad_top': '#5CB5FF',
        'grad_hi': '#40A6FF',
        'grad_mid': '#2693FF',
        'grad_low': '#147DE8',
        'border_glow': '#75C1FF',
        'on_primary': '#050811',
        'bg_c1': '#11151C',
        'bg_c2': '#151A24',
        'bg_c3': '#121620',
        'surface': 'rgba(26, 32, 45, 0.70)',
        'surface_hi': 'rgba(34, 42, 58, 0.82)',
        'navbar': 'rgba(18, 22, 31, 0.92)',
        'text': '#F1F5F9',
        'text_muted': '#8FA0B8',
    },
    'Emerald Green': {
        'name': 'Emerald Green',
        'primary': '#10B981',
        'primary_hov': '#34D399',
        'primary_pressed': '#059669',
        'primary_dim': 'rgba(16, 185, 129, 0.15)',
        'grad_top': '#6EE7B7',
        'grad_hi': '#34D399',
        'grad_mid': '#10B981',
        'grad_low': '#059669',
        'border_glow': '#A7F3D0',
        'on_primary': '#021B11',
        'bg_c1': '#0D1714',
        'bg_c2': '#12211C',
        'bg_c3': '#0E1915',
        'surface': 'rgba(18, 38, 32, 0.70)',
        'surface_hi': 'rgba(25, 52, 44, 0.82)',
        'navbar': 'rgba(12, 24, 20, 0.92)',
        'text': '#F1F5F9',
        'text_muted': '#8FA0B8',
    },
    'Cyber Purple': {
        'name': 'Cyber Purple',
        'primary': '#A855F7',
        'primary_hov': '#C084FC',
        'primary_pressed': '#9333EA',
        'primary_dim': 'rgba(168, 85, 247, 0.15)',
        'grad_top': '#E9D5FF',
        'grad_hi': '#C084FC',
        'grad_mid': '#A855F7',
        'grad_low': '#7E22CE',
        'border_glow': '#F3E8FF',
        'on_primary': '#160228',
        'bg_c1': '#15101F',
        'bg_c2': '#1D142C',
        'bg_c3': '#161021',
        'surface': 'rgba(38, 25, 56, 0.70)',
        'surface_hi': 'rgba(52, 34, 78, 0.82)',
        'navbar': 'rgba(21, 14, 32, 0.92)',
        'text': '#F1F5F9',
        'text_muted': '#A798C2',
    },
    'Crimson Sunset': {
        'name': 'Crimson Sunset',
        'primary': '#F43F5E',
        'primary_hov': '#FB7185',
        'primary_pressed': '#E11D48',
        'primary_dim': 'rgba(244, 63, 94, 0.15)',
        'grad_top': '#FECDD3',
        'grad_hi': '#FB7185',
        'grad_mid': '#F43F5E',
        'grad_low': '#BE123C',
        'border_glow': '#FFE4E6',
        'on_primary': '#22040A',
        'bg_c1': '#1B0F13',
        'bg_c2': '#26141B',
        'bg_c3': '#1E1015',
        'surface': 'rgba(48, 22, 30, 0.70)',
        'surface_hi': 'rgba(64, 30, 41, 0.82)',
        'navbar': 'rgba(26, 12, 17, 0.92)',
        'text': '#F1F5F9',
        'text_muted': '#BFA2AC',
    },
    'Amber Gold': {
        'name': 'Amber Gold',
        'primary': '#F59E0B',
        'primary_hov': '#FBBF24',
        'primary_pressed': '#D97706',
        'primary_dim': 'rgba(245, 158, 11, 0.15)',
        'grad_top': '#FDE68A',
        'grad_hi': '#FBBF24',
        'grad_mid': '#F59E0B',
        'grad_low': '#B45309',
        'border_glow': '#FEF3C7',
        'on_primary': '#241401',
        'bg_c1': '#1A160E',
        'bg_c2': '#241F13',
        'bg_c3': '#1C180F',
        'surface': 'rgba(44, 36, 20, 0.70)',
        'surface_hi': 'rgba(60, 49, 28, 0.82)',
        'navbar': 'rgba(25, 20, 11, 0.92)',
        'text': '#F1F5F9',
        'text_muted': '#BAAF98',
    },
    'Minimal Monochrome': {
        'name': 'Minimal Monochrome',
        'primary': '#FFFFFF',
        'primary_hov': '#F1F5F9',
        'primary_pressed': '#E2E8F0',
        'primary_dim': 'rgba(255, 255, 255, 0.16)',
        'grad_top': '#FFFFFF',
        'grad_hi': '#F8FAFC',
        'grad_mid': '#F1F5F9',
        'grad_low': '#E2E8F0',
        'border_glow': '#FFFFFF',
        'on_primary': '#000000',
        'bg_c1': '#000000',
        'bg_c2': '#050505',
        'bg_c3': '#000000',
        'surface': 'rgba(16, 16, 16, 0.85)',
        'surface_hi': 'rgba(26, 26, 26, 0.90)',
        'navbar': 'rgba(8, 8, 8, 0.95)',
        'text': '#FFFFFF',
        'text_muted': '#9CA3AF',
    },
    'Pure Pitch Black': {
        'name': 'Pure Pitch Black',
        'primary': '#38BDF8',
        'primary_hov': '#7DD3FC',
        'primary_pressed': '#0284C7',
        'primary_dim': 'rgba(56, 189, 248, 0.15)',
        'grad_top': '#BAE6FD',
        'grad_hi': '#7DD3FC',
        'grad_mid': '#38BDF8',
        'grad_low': '#0284C7',
        'border_glow': '#E0F2FE',
        'on_primary': '#02182B',
        'bg_c1': '#000000',
        'bg_c2': '#030304',
        'bg_c3': '#000000',
        'surface': 'rgba(10, 12, 16, 0.85)',
        'surface_hi': 'rgba(18, 20, 26, 0.90)',
        'navbar': 'rgba(5, 6, 8, 0.95)',
        'text': '#F8FAFC',
        'text_muted': '#94A3B8',
    },
    'Deep Midnight Navy': {
        'name': 'Deep Midnight Navy',
        'primary': '#00D2FF',
        'primary_hov': '#40DCFF',
        'primary_pressed': '#00A0C6',
        'primary_dim': 'rgba(0, 210, 255, 0.15)',
        'grad_top': '#A6EFFF',
        'grad_hi': '#54E2FF',
        'grad_mid': '#00D2FF',
        'grad_low': '#0090B3',
        'border_glow': '#C4F6FF',
        'on_primary': '#011520',
        'bg_c1': '#070C18',
        'bg_c2': '#0B1428',
        'bg_c3': '#080E1C',
        'surface': 'rgba(14, 25, 50, 0.70)',
        'surface_hi': 'rgba(20, 36, 72, 0.82)',
        'navbar': 'rgba(8, 15, 30, 0.92)',
        'text': '#F1F5F9',
        'text_muted': '#8FA0B8',
    },
    'Neon Toxic': {
        'name': 'Neon Toxic',
        'primary': '#39FF14',
        'primary_hov': '#66FF47',
        'primary_pressed': '#28CC0D',
        'primary_dim': 'rgba(57, 255, 20, 0.15)',
        'grad_top': '#B3FF99',
        'grad_hi': '#66FF47',
        'grad_mid': '#39FF14',
        'grad_low': '#22AA0B',
        'border_glow': '#D6FFC7',
        'on_primary': '#031900',
        'bg_c1': '#091507',
        'bg_c2': '#10220C',
        'bg_c3': '#0B1708',
        'surface': 'rgba(18, 40, 14, 0.70)',
        'surface_hi': 'rgba(26, 56, 20, 0.82)',
        'navbar': 'rgba(10, 22, 8, 0.92)',
        'text': '#F1F5F9',
        'text_muted': '#93B08C',
    },
    'Rose Quartz': {
        'name': 'Rose Quartz',
        'primary': '#EC4899',
        'primary_hov': '#F472B6',
        'primary_pressed': '#DB2777',
        'primary_dim': 'rgba(236, 72, 153, 0.15)',
        'grad_top': '#FBCFE8',
        'grad_hi': '#F472B6',
        'grad_mid': '#EC4899',
        'grad_low': '#BE185D',
        'border_glow': '#FCE7F3',
        'on_primary': '#260214',
        'bg_c1': '#180B14',
        'bg_c2': '#24101E',
        'bg_c3': '#1B0C16',
        'surface': 'rgba(46, 20, 38, 0.70)',
        'surface_hi': 'rgba(64, 28, 54, 0.82)',
        'navbar': 'rgba(24, 10, 20, 0.92)',
        'text': '#F1F5F9',
        'text_muted': '#BFA2B3',
    },
    'Solar Flare': {
        'name': 'Solar Flare',
        'primary': '#FF5E00',
        'primary_hov': '#FF7A29',
        'primary_pressed': '#D95000',
        'primary_dim': 'rgba(255, 94, 0, 0.15)',
        'grad_top': '#FFD1B3',
        'grad_hi': '#FF8F4D',
        'grad_mid': '#FF5E00',
        'grad_low': '#C74800',
        'border_glow': '#FFE5D6',
        'on_primary': '#260A00',
        'bg_c1': '#1B0F09',
        'bg_c2': '#26150D',
        'bg_c3': '#1E110A',
        'surface': 'rgba(50, 26, 16, 0.70)',
        'surface_hi': 'rgba(68, 36, 22, 0.82)',
        'navbar': 'rgba(26, 13, 8, 0.92)',
        'text': '#F1F5F9',
        'text_muted': '#BCA89E',
    },
    'Ghost White': {
        'name': 'Ghost White',
        'primary': '#0EA5E9',
        'primary_hov': '#38BDF8',
        'primary_pressed': '#0284C7',
        'primary_dim': 'rgba(14, 165, 233, 0.15)',
        'grad_top': '#E0F2FE',
        'grad_hi': '#7DD3FC',
        'grad_mid': '#0EA5E9',
        'grad_low': '#0369A1',
        'border_glow': '#F0F9FF',
        'on_primary': '#FFFFFF',
        'bg_c1': '#E2E8F0',
        'bg_c2': '#ECEFF4',
        'bg_c3': '#E5E9F0',
        'surface': 'rgba(255, 255, 255, 0.85)',
        'surface_hi': 'rgba(255, 255, 255, 0.95)',
        'navbar': 'rgba(241, 245, 249, 0.95)',
        'text': '#0F172A',
        'text_muted': '#475569',
    },
    'Cyberpunk Teal': {
        'name': 'Cyberpunk Teal',
        'primary': '#14B8A6',
        'primary_hov': '#2DD4BF',
        'primary_pressed': '#0D9488',
        'primary_dim': 'rgba(20, 184, 166, 0.15)',
        'grad_top': '#99F6E4',
        'grad_hi': '#2DD4BF',
        'grad_mid': '#14B8A6',
        'grad_low': '#0F766E',
        'border_glow': '#CCFBF1',
        'on_primary': '#021B18',
        'bg_c1': '#091515',
        'bg_c2': '#0D2121',
        'bg_c3': '#0A1919',
        'surface': 'rgba(18, 40, 40, 0.70)',
        'surface_hi': 'rgba(26, 56, 56, 0.82)',
        'navbar': 'rgba(10, 22, 22, 0.92)',
        'text': '#F1F5F9',
        'text_muted': '#8EA8A8',
    },
}

CURRENT_THEME = 'Electric Blue'

TOKENS = {
    'bg':           '#151922',
    'bg_gradient':  'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #11141B, stop:0.5 #161A24, stop:1 #131720)',
    'navbar':       'rgba(18, 22, 31, 0.92)',
    'sidebar':      'rgba(18, 22, 31, 0.92)',
    'surface':      'rgba(26, 32, 45, 0.70)',
    'surface_hi':   'rgba(34, 42, 58, 0.82)',
    'surface_glow': 'rgba(41, 152, 255, 0.10)',
    'border':       'rgba(255, 255, 255, 0.07)',
    'border_hi':    'rgba(255, 255, 255, 0.15)',
    'border_glow':  'rgba(41, 152, 255, 0.40)',
    'text':         '#F1F5F9',
    'text_muted':   '#8FA0B8',
    'text_faint':   '#475569',

    'primary':          THEME_TEMPLATES['Electric Blue']['primary'],
    'primary_hov':      THEME_TEMPLATES['Electric Blue']['primary_hov'],
    'primary_pressed':  THEME_TEMPLATES['Electric Blue']['primary_pressed'],
    'primary_dim':      THEME_TEMPLATES['Electric Blue']['primary_dim'],
    'on_primary':       THEME_TEMPLATES['Electric Blue']['on_primary'],

    'grad_top':     THEME_TEMPLATES['Electric Blue']['grad_top'],
    'grad_hi':      THEME_TEMPLATES['Electric Blue']['grad_hi'],
    'grad_mid':     THEME_TEMPLATES['Electric Blue']['grad_mid'],
    'grad_low':     THEME_TEMPLATES['Electric Blue']['grad_low'],
    'btn_border':   THEME_TEMPLATES['Electric Blue']['border_glow'],

    'danger':       '#F87171',
    'danger_hov':   '#EF4444',
    'danger_dim':   'rgba(248, 113, 113, 0.15)',

    'neutral':      'rgba(255, 255, 255, 0.05)',
    'neutral_hov':  'rgba(255, 255, 255, 0.10)',
    'neutral_dark': 'rgba(255, 255, 255, 0.03)',
    'neutral_dark_hov': 'rgba(255, 255, 255, 0.07)',
}

SPACING = {'xs': 4, 'sm': 8, 'md': 12, 'lg': 16, 'xl': 24}
RADIUS = 12
NAV_HEIGHT = 56
WINDOW_DEFAULT = (1040, 720)
WINDOW_MIN = (800, 560)
SANS_FONT = 'Segoe UI'
MONO_FONT = 'Consolas'


def set_theme_template(name: str):
    global CURRENT_THEME, TOKENS
    if name not in THEME_TEMPLATES:
        return
    CURRENT_THEME = name
    tmpl = THEME_TEMPLATES[name]
    TOKENS['primary'] = tmpl['primary']
    TOKENS['primary_hov'] = tmpl['primary_hov']
    TOKENS['primary_pressed'] = tmpl['primary_pressed']
    TOKENS['primary_dim'] = tmpl['primary_dim']
    TOKENS['on_primary'] = tmpl['on_primary']
    TOKENS['grad_top'] = tmpl['grad_top']
    TOKENS['grad_hi'] = tmpl['grad_hi']
    TOKENS['grad_mid'] = tmpl['grad_mid']
    TOKENS['grad_low'] = tmpl['grad_low']
    TOKENS['btn_border'] = tmpl['border_glow']
    if 'bg_c1' in tmpl:
        TOKENS['bg_c1'] = tmpl['bg_c1']
        TOKENS['bg_c2'] = tmpl['bg_c2']
        TOKENS['bg_c3'] = tmpl['bg_c3']
        TOKENS['bg'] = tmpl['bg_c2']
    if 'surface' in tmpl:
        TOKENS['surface'] = tmpl['surface']
    if 'surface_hi' in tmpl:
        TOKENS['surface_hi'] = tmpl['surface_hi']
    if 'navbar' in tmpl:
        TOKENS['navbar'] = tmpl['navbar']
    if 'text' in tmpl:
        TOKENS['text'] = tmpl['text']
    if 'text_muted' in tmpl:
        TOKENS['text_muted'] = tmpl['text_muted']


def build_stylesheet():
    t = TOKENS
    return f"""
QWidget {{
    background-color: transparent;
    color: {t['text']};
    font-family: '{SANS_FONT}';
    font-size: 13px;
}}
QLabel {{ background: transparent; padding: 0; margin: 0; }}

/* Cards with Frosted Glossy Dark look */
QFrame#Card {{
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS}px;
}}
QFrame#Card:hover {{
    border: 1px solid {t['border_hi']};
}}
QFrame#Card[variant="status"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t['primary_dim']}, stop:1 rgba(26,32,45,0.70));
    border: 1px solid {t['primary']};
    border-left: 4px solid {t['primary']};
    border-radius: {RADIUS}px;
}}
QFrame#Card[variant="extras"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t['primary_dim']}, stop:1 rgba(26,32,45,0.65));
    border: 1px solid {t['primary_dim']};
    border-radius: {RADIUS}px;
}}

/* Top Navigation Bar */
QFrame#NavBar {{
    background: {t['navbar']};
    border-bottom: 1px solid {t['border_hi']};
}}

QPushButton[role="nav_tab"] {{
    background: transparent;
    border: none;
    border-radius: 9px;
    padding: 7px 18px;
    font-size: 13px;
    font-weight: 700;
    color: {t['text_muted']};
}}
QPushButton[role="nav_tab"]:hover {{
    color: {t['text']};
    background: {t['neutral']};
}}
QPushButton[role="nav_tab"]:checked {{
    color: {t['on_primary']};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 {t['grad_top']}, stop:0.08 {t['grad_hi']}, stop:0.5 {t['grad_mid']}, stop:1 {t['grad_low']});
    border: 1px solid {t['btn_border']};
    font-weight: 800;
}}

/* Labels */
QLabel#SectionTitle {{
    color: {t['text_muted']};
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 1.2px;
    background: transparent;
}}
QLabel#SectionTitle:disabled {{ color: {t['text_faint']}; }}
QLabel#DurationUnit:disabled {{ color: {t['text_faint']}; }}
QLabel#PageTitle {{
    font-size: 20px;
    font-weight: 700;
    color: {t['text']};
    background: transparent;
}}
QLabel#StatValue {{
    font-family: '{MONO_FONT}';
    font-size: 15px;
    font-weight: 700;
    color: {t['text']};
    background: transparent;
}}
QLabel#StatTitle {{
    color: {t['text_muted']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    background: transparent;
}}
QLabel#Brand {{
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 0.5px;
    background: transparent;
}}

/* Buttons with Glossy Lighting & Black Text */
QPushButton {{
    border: none;
    border-radius: 9px;
    padding: 7px 16px;
    min-height: 32px;
    font-weight: 700;
}}

/* Primary Button: Glossy Theme Gradient + Bold Contrast Text */
QPushButton[role="primary"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 {t['grad_top']}, stop:0.07 {t['grad_hi']}, stop:0.48 {t['grad_mid']}, stop:1 {t['grad_low']});
    color: {t['on_primary']};
    border: 1px solid {t['btn_border']};
}}
QPushButton[role="primary"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #FFFFFF, stop:0.07 {t['grad_top']}, stop:0.48 {t['primary_hov']}, stop:1 {t['grad_mid']});
    color: {t['on_primary']};
    border: 1px solid #FFFFFF;
}}
QPushButton[role="primary"]:pressed {{
    background: {t['primary_pressed']};
    color: {t['on_primary']};
    border: 1px solid {t['primary_pressed']};
}}
QPushButton[role="primary"]:disabled {{
    background: {t['primary_dim']};
    color: {t['text_faint']};
    border: 1px solid rgba(255, 255, 255, 0.05);
}}

/* Danger Button: Subtle Glossy Red */
QPushButton[role="danger"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #FFA3A3, stop:0.07 #FF7A7A, stop:0.5 #F87171, stop:1 #E04848);
    color: #1A0505;
    border: 1px solid #FFB8B8;
}}
QPushButton[role="danger"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #FFB5B5, stop:0.07 #FF8C8C, stop:0.5 #FA8282, stop:1 #EB5757);
    border: 1px solid #FFC9C9;
}}
QPushButton[role="danger"]:pressed {{
    background: #C53030;
    color: #000000;
}}
QPushButton[role="danger"]:disabled {{
    background-color: {t['danger_dim']};
    color: {t['text_faint']};
    border: none;
}}

/* Neutral Button */
QPushButton[role="neutral"] {{
    background-color: {t['neutral']};
    color: {t['text']};
    border: 1px solid {t['border']};
}}
QPushButton[role="neutral"]:hover {{
    background-color: {t['neutral_hov']};
    border-color: {t['border_hi']};
}}

/* Chip Button */
QPushButton[role="chip"] {{
    background-color: {t['neutral_dark']};
    color: {t['text']};
    padding: 4px 12px;
    min-height: 26px;
    border: 1px solid {t['border']};
    border-radius: 6px;
    font-size: 12px;
}}
QPushButton[role="chip"]:hover {{
    background-color: {t['neutral_dark_hov']};
    border-color: {t['border_hi']};
}}
QPushButton[role="chip"]:disabled {{ color: {t['text_faint']}; }}

/* Segment Button (Home Village, Builder Base, Valkyries, etc.) */
QPushButton[role="segment"] {{
    background: transparent;
    border: 1px solid {t['border']};
    color: {t['text_muted']};
    border-radius: 8px;
    font-weight: 700;
}}
QPushButton[role="segment"]:hover:!checked {{
    border-color: {t['border_hi']};
    color: {t['text']};
    background: {t['neutral']};
}}
QPushButton[role="segment"]:checked {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 {t['grad_top']}, stop:0.08 {t['grad_hi']}, stop:0.5 {t['grad_mid']}, stop:1 {t['grad_low']});
    color: {t['on_primary']};
    border: 1px solid {t['btn_border']};
}}
QPushButton[role="segment"][underDevelopment="true"] {{
    color: {t['text_faint']};
    border-color: rgba(255, 255, 255, 0.05);
}}

/* Inputs */
QLineEdit, QSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    background: {t['surface_hi']};
    border: 1px solid {t['border']};
    border-radius: 10px;
    padding: 6px 10px;
    color: {t['text']};
    selection-background-color: {t['primary_hov']};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {t['primary']};
}}

/* Strategy Dropdown Styled Picker */
QComboBox#StrategyPicker {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 {t['grad_top']}, 
        stop:0.08 {t['grad_hi']}, 
        stop:0.5 {t['grad_mid']}, 
        stop:1 {t['grad_low']});
    border: 1px solid {t['btn_border']};
    border-radius: 9px;
    padding: 6px 36px 6px 14px;
    font-size: 13px;
    font-weight: 800;
    color: {t['on_primary']};
}}
QComboBox#StrategyPicker:hover {{
    border-color: #FFFFFF;
}}
QComboBox#StrategyPicker::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
    background: transparent;
}}
QComboBox#StrategyPicker::down-arrow {{
    image: url("assets/dropdown_arrow_dark.png");
    width: 12px;
    height: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: #141A25;
    background: #141A25;
    border: 1px solid {t['border_hi']};
    border-radius: 10px;
    selection-background-color: {t['primary']};
    selection-color: {t['on_primary']};
    color: #F8FAFC;
    outline: none;
    padding: 5px;
}}
QComboBox QAbstractItemView::item {{
    min-height: 32px;
    padding: 5px 12px;
    border-radius: 6px;
    color: #F8FAFC;
    font-weight: 600;
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: rgba(255, 255, 255, 0.10);
    color: #FFFFFF;
}}
QComboBox QAbstractItemView::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 {t['grad_top']}, stop:0.08 {t['grad_hi']}, stop:0.5 {t['grad_mid']}, stop:1 {t['grad_low']});
    color: {t['on_primary']};
    font-weight: 800;
}}
QSpinBox#DurationSpin {{
    font-family: '{MONO_FONT}';
    font-size: 14px;
    font-weight: 700;
    min-height: 30px; max-height: 30px;
    padding: 2px 8px;
}}
QSpinBox:disabled, QSpinBox#DurationSpin:disabled {{
    color: {t['text_faint']};
    background: {t['surface']};
    border-color: rgba(255, 255, 255, 0.04);
}}

/* QSpinBox Arrow / Stepper Buttons: Vibrant theme fill with dark arrow */
QSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 {t['grad_top']}, stop:0.1 {t['grad_hi']}, stop:0.5 {t['grad_mid']}, stop:1 {t['grad_low']});
    border-top-right-radius: 7px;
    border-left: 1px solid {t['border']};
    border-bottom: 1px solid {t['border']};
}}
QSpinBox::up-button:hover {{
    background: {t['primary_hov']};
}}
QSpinBox::up-button:pressed {{
    background: {t['primary_pressed']};
}}
QSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 {t['grad_top']}, stop:0.1 {t['grad_hi']}, stop:0.5 {t['grad_mid']}, stop:1 {t['grad_low']});
    border-bottom-right-radius: 7px;
    border-left: 1px solid {t['border']};
}}
QSpinBox::down-button:hover {{
    background: {t['primary_hov']};
}}
QSpinBox::down-button:pressed {{
    background: {t['primary_pressed']};
}}
QSpinBox::up-arrow {{
    width: 9px;
    height: 6px;
    image: url("assets/arrow_up.png");
}}
QSpinBox::down-arrow {{
    width: 9px;
    height: 6px;
    image: url("assets/arrow_down.png");
}}

/* Steppers */
QPushButton[role="stepper"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 {t['grad_top']}, stop:0.1 {t['grad_hi']}, stop:0.5 {t['grad_mid']}, stop:1 {t['grad_low']});
    padding: 0;
    min-height: 14px; max-height: 14px;
    min-width: 24px; max-width: 24px;
    border-radius: 5px;
    border: 1px solid {t['btn_border']};
}}
QPushButton[role="stepper"]:hover  {{ background: {t['primary_hov']}; border-color: #FFFFFF; }}
QPushButton[role="stepper"]:pressed {{ background: {t['primary_pressed']}; }}
QPushButton[role="stepper"]:disabled {{ background: rgba(255, 255, 255, 0.04); border-color: transparent; }}

/* Help / icon */
QPushButton[role="help"] {{
    background: transparent;
    color: {t['text_muted']};
    padding: 0;
    min-height: 20px; min-width: 20px;
    max-height: 20px; max-width: 20px;
    border-radius: 10px;
    border: 1px solid {t['border_hi']};
    font-size: 11px; font-weight: 700;
}}
QPushButton[role="help"]:hover {{
    color: {t['text']};
    border-color: rgba(255, 255, 255, 0.4);
    background: {t['neutral']};
}}
QPushButton[role="icon"] {{
    background: {t['neutral']};
    color: {t['text']};
    padding: 0;
    min-height: 34px; min-width: 34px;
    max-height: 34px; max-width: 34px;
    border-radius: 8px;
    border: 1px solid {t['border']};
}}
QPushButton[role="icon"]:hover  {{ background: {t['neutral_hov']}; }}
QPushButton[role="icon"]:checked {{ 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 {t['grad_top']}, stop:0.08 {t['grad_hi']}, stop:0.5 {t['grad_mid']}, stop:1 {t['grad_low']});
    color: {t['on_primary']};
    border: 1px solid {t['btn_border']};
}}

/* Status bar */
QStatusBar {{
    background: #0E1219;
    border-top: 1px solid {t['border']};
    font-family: '{MONO_FONT}';
    font-size: 11px;
    color: {t['text_muted']};
}}
QStatusBar::item {{ border: none; }}

/* Scroll */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 6px; margin: 4px 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.12);
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: rgba(255, 255, 255, 0.25); }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

/* Toggle */
QCheckBox#ToggleSwitch {{ spacing: 0; background: transparent; }}
QCheckBox#ToggleSwitch::indicator {{ width: 0; height: 0; border: none; }}
"""


def apply_theme(app, theme_name: str | None = None):
    if theme_name:
        set_theme_template(theme_name)
    app.setStyle('Fusion')
    pal = QPalette()
    pal.setColor(QPalette.Window,          QColor(TOKENS['bg']))
    pal.setColor(QPalette.Base,            QColor('#10141D'))
    pal.setColor(QPalette.AlternateBase,   QColor('#171C27'))
    pal.setColor(QPalette.Text,            QColor(TOKENS['text']))
    pal.setColor(QPalette.WindowText,      QColor(TOKENS['text']))
    pal.setColor(QPalette.Button,          QColor('#1A212E'))
    pal.setColor(QPalette.ButtonText,      QColor(TOKENS['text']))
    pal.setColor(QPalette.ToolTipBase,     QColor('#222B3B'))
    pal.setColor(QPalette.ToolTipText,     QColor(TOKENS['text']))
    pal.setColor(QPalette.Highlight,       QColor(TOKENS['primary_hov']))
    pal.setColor(QPalette.HighlightedText, QColor(TOKENS['on_primary']))
    app.setPalette(pal)
    app.setStyleSheet(build_stylesheet())


STYLESHEET = build_stylesheet()
