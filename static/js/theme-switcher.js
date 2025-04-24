const ThemeManager = {
  STORAGE_KEY: 'theme',
  DEFAULT_THEME: 'light',

  init() {
    try {
      const toggles = document.querySelectorAll('.themeToggle');
      const icons = document.querySelectorAll('.themeIcon');
      const html = document.documentElement;

      if (!toggles.length || !icons.length || !html) {
        console.warn('Theme toggle elements not found');
        return;
      }

      // Load saved theme with fallback
      const savedTheme = this.loadTheme();
      this.applyTheme(savedTheme, { html, icons });

      // Set up click events for all toggles
      toggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
          const currentTheme = html.getAttribute('data-bs-theme');
          const newTheme = currentTheme === 'light' ? 'dark' : 'light';
          this.applyTheme(newTheme, { html, icons });
          this.saveTheme(newTheme);
        });
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

  applyTheme(theme, { html, icons }) {
    html.setAttribute('data-bs-theme', theme);
    icons.forEach(icon => {
      icon.className = `themeIcon bi bi-${theme === 'light' ? 'moon' : 'sun'} fs-5`;
    });

    window.dispatchEvent(new CustomEvent('themechange', {
      detail: { theme }
    }));
  }
};

document.addEventListener('DOMContentLoaded', () => {
  ThemeManager.init();
});
