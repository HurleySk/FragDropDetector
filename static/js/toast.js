// Lightweight Toast Notification System

class ToastManager {
    constructor() {
        this.container = null;
        this.toasts = new Map();
        this.init();
    }

    init() {
        this.container = document.createElement('div');
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', options = {}) {
        const {
            title = null,
            duration = 4000,
            persistent = false
        } = options;

        const toastId = Date.now().toString();
        const toast = this.createToast(toastId, message, type, title, persistent);

        this.container.appendChild(toast);
        this.toasts.set(toastId, toast);

        // Trigger show animation
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // Auto dismiss unless persistent
        if (!persistent && duration > 0) {
            const progressBar = toast.querySelector('.toast-progress');
            if (progressBar) {
                progressBar.style.width = '0%';
                progressBar.style.transitionDuration = `${duration}ms`;
            }

            setTimeout(() => this.dismiss(toastId), duration);
        }

        return toastId;
    }

    createToast(id, message, type, title, persistent) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.dataset.toastId = id;

        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'i'
        };

        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.info}</div>
            <div class="toast-content">
                ${title ? `<div class="toast-title">${title}</div>` : ''}
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="window.toastManager.dismiss('${id}')">&times;</button>
            ${!persistent ? '<div class="toast-progress"></div>' : ''}
        `;

        return toast;
    }

    dismiss(toastId) {
        const toast = this.toasts.get(toastId);
        if (!toast) return;

        toast.classList.add('hide');
        toast.classList.remove('show');

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            this.toasts.delete(toastId);
        }, 300);
    }

    success(message, options = {}) {
        return this.show(message, 'success', options);
    }

    error(message, options = {}) {
        return this.show(message, 'error', options);
    }

    warning(message, options = {}) {
        return this.show(message, 'warning', options);
    }

    info(message, options = {}) {
        return this.show(message, 'info', options);
    }

    clear() {
        this.toasts.forEach((toast, id) => {
            this.dismiss(id);
        });
    }
}

// Initialize toast manager
window.toastManager = new ToastManager();