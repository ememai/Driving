const ThemeManager = {
  STORAGE_KEY: 'theme',
  DEFAULT_THEME: 'light',

  init() {
    try {
      const toggle = document.getElementById('themeToggle');
      const icon = document.getElementById('themeIcon');
      const html = document.documentElement;

      if (!toggle || !icon || !html) {
        console.warn('Theme toggle elements not found');
        return;
      }

      // Load saved theme with fallback
      const savedTheme = this.loadTheme();
      this.applyTheme(savedTheme, { html, icon });

      // Set up click event
      toggle.addEventListener('click', () => {
        const currentTheme = html.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme, { html, icon });
        this.saveTheme(newTheme);
      });

    } catch (error) {
      console.error('Error initializing theme system:', error);
    }
  },

  loadTheme() {
    return localStorage.getItem(this.STORAGE_KEY) || this.DEFAULT_THEME;
  },

  saveTheme(theme) {
    localStorage.setItem(this.STORAGE_KEY, theme);
  },

  applyTheme(theme, { html, icon }) {
    html.setAttribute('data-bs-theme', theme);
    icon.className = `bi bi-${theme === 'light' ? 'moon' : 'sun'} fs-5`;

    window.dispatchEvent(new CustomEvent('themechange', {
      detail: { theme }
    }));
  }
};

document.addEventListener('DOMContentLoaded', () => {
  ThemeManager.init();
});
