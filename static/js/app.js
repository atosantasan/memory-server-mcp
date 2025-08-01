// Memory Server MCP WebUI - Main JavaScript File

// Global configuration
const CONFIG = {
    API_BASE_URL: '/api',
    DEBOUNCE_DELAY: 300,
    AUTO_SAVE_DELAY: 2000,
    MAX_RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000
};

// Global state
const STATE = {
    isLoading: false,
    currentSearch: null,
    retryCount: 0
};

// Utility functions
const Utils = {
    /**
     * Debounce function to limit the rate of function calls
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Throttle function to limit function calls to once per interval
     */
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * Escape HTML to prevent XSS attacks
     */
    escapeHtml: function(text) {
        if (typeof text !== 'string') return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Format date to Japanese locale string
     */
    formatDate: function(dateString) {
        if (!dateString) return '';
        try {
            const date = new Date(dateString);
            return date.toLocaleString('ja-JP', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (e) {
            return dateString;
        }
    },

    /**
     * Parse comma-separated values into array
     */
    parseCommaSeparated: function(value) {
        if (!value || typeof value !== 'string') return [];
        return value.split(',')
            .map(item => item.trim())
            .filter(item => item.length > 0);
    },

    /**
     * Generate unique ID for elements
     */
    generateId: function() {
        return 'id_' + Math.random().toString(36).substr(2, 9);
    },

    /**
     * Copy text to clipboard
     */
    copyToClipboard: async function(text) {
        try {
            await navigator.clipboard.writeText(text);
            Notifications.showSuccess('クリップボードにコピーしました');
            return true;
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            Notifications.showSuccess('クリップボードにコピーしました');
            return true;
        }
    },

    /**
     * Check if device is mobile
     */
    isMobile: function() {
        return window.innerWidth <= 768;
    }
};

// API client with error handling and retry logic
const ApiClient = {
    /**
     * Make HTTP request with error handling
     */
    request: async function(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };

        const requestOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(CONFIG.API_BASE_URL + url, requestOptions);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error?.message || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },

    /**
     * GET request
     */
    get: async function(url) {
        return await this.request(url, { method: 'GET' });
    },

    /**
     * POST request
     */
    post: async function(url, data) {
        return await this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    /**
     * PUT request
     */
    put: async function(url, data) {
        return await this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    /**
     * DELETE request
     */
    delete: async function(url) {
        return await this.request(url, { method: 'DELETE' });
    },

    /**
     * Request with retry logic
     */
    requestWithRetry: async function(url, options = {}, maxRetries = CONFIG.MAX_RETRY_ATTEMPTS) {
        let lastError;
        
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                return await this.request(url, options);
            } catch (error) {
                lastError = error;
                
                if (attempt < maxRetries) {
                    console.warn(`Request failed, retrying (${attempt + 1}/${maxRetries})...`);
                    await new Promise(resolve => setTimeout(resolve, CONFIG.RETRY_DELAY * (attempt + 1)));
                }
            }
        }
        
        throw lastError;
    }
};

// Loading indicator management
const LoadingManager = {
    elements: new Map(),

    /**
     * Show loading indicator
     */
    show: function(elementId = 'loadingIndicator') {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = 'block';
            this.elements.set(elementId, true);
        }
        STATE.isLoading = true;
    },

    /**
     * Hide loading indicator
     */
    hide: function(elementId = 'loadingIndicator') {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = 'none';
            this.elements.set(elementId, false);
        }
        
        // Check if any loading indicators are still active
        const hasActiveLoading = Array.from(this.elements.values()).some(active => active);
        STATE.isLoading = hasActiveLoading;
    },

    /**
     * Toggle loading indicator
     */
    toggle: function(show, elementId = 'loadingIndicator') {
        if (show) {
            this.show(elementId);
        } else {
            this.hide(elementId);
        }
    },

    /**
     * Create and show overlay loading
     */
    showOverlay: function(message = '読み込み中...') {
        this.hideOverlay(); // Remove any existing overlay
        
        const overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-light mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="text-light">${Utils.escapeHtml(message)}</div>
            </div>
        `;
        
        document.body.appendChild(overlay);
    },

    /**
     * Hide overlay loading
     */
    hideOverlay: function() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.remove();
        }
    }
};

// Notification system
const Notifications = {
    /**
     * Show notification
     */
    show: function(message, type = 'info', duration = 5000) {
        const alertDiv = document.createElement('div');
        const alertId = Utils.generateId();
        
        alertDiv.id = alertId;
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas ${this.getIcon(type)} me-2"></i>
                <div class="flex-grow-1">${Utils.escapeHtml(message)}</div>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        // Insert at the top of the container
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
        } else {
            document.body.insertBefore(alertDiv, document.body.firstChild);
        }
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                const element = document.getElementById(alertId);
                if (element) {
                    element.remove();
                }
            }, duration);
        }
        
        // Add click handler to close button
        const closeButton = alertDiv.querySelector('.btn-close');
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                alertDiv.remove();
            });
        }
        
        return alertId;
    },

    /**
     * Show success notification
     */
    showSuccess: function(message, duration = 5000) {
        return this.show(message, 'success', duration);
    },

    /**
     * Show error notification
     */
    showError: function(message, duration = 8000) {
        return this.show(message, 'danger', duration);
    },

    /**
     * Show warning notification
     */
    showWarning: function(message, duration = 6000) {
        return this.show(message, 'warning', duration);
    },

    /**
     * Show info notification
     */
    showInfo: function(message, duration = 5000) {
        return this.show(message, 'info', duration);
    },

    /**
     * Get icon for notification type
     */
    getIcon: function(type) {
        const icons = {
            success: 'fa-check-circle',
            danger: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle',
            primary: 'fa-info-circle',
            secondary: 'fa-info-circle'
        };
        return icons[type] || 'fa-info-circle';
    },

    /**
     * Clear all notifications
     */
    clearAll: function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => alert.remove());
    }
};

// Form validation utilities
const FormValidator = {
    /**
     * Validate required fields
     */
    validateRequired: function(formElement) {
        const requiredFields = formElement.querySelectorAll('[required]');
        let isValid = true;
        const errors = [];

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                this.showFieldError(field, 'この項目は必須です');
                errors.push(`${this.getFieldLabel(field)}は必須です`);
            } else {
                this.clearFieldError(field);
            }
        });

        return { isValid, errors };
    },

    /**
     * Show field error
     */
    showFieldError: function(field, message) {
        field.classList.add('is-invalid');
        
        // Remove existing error message
        this.clearFieldError(field);
        
        // Add new error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
    },

    /**
     * Clear field error
     */
    clearFieldError: function(field) {
        field.classList.remove('is-invalid');
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    },

    /**
     * Get field label
     */
    getFieldLabel: function(field) {
        const label = field.parentNode.querySelector('label');
        return label ? label.textContent.replace('*', '').trim() : field.name || 'フィールド';
    }
};

// Local storage utilities
const Storage = {
    /**
     * Save data to local storage
     */
    save: function(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
            return true;
        } catch (error) {
            console.error('Failed to save to localStorage:', error);
            return false;
        }
    },

    /**
     * Load data from local storage
     */
    load: function(key, defaultValue = null) {
        try {
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : defaultValue;
        } catch (error) {
            console.error('Failed to load from localStorage:', error);
            return defaultValue;
        }
    },

    /**
     * Remove data from local storage
     */
    remove: function(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('Failed to remove from localStorage:', error);
            return false;
        }
    },

    /**
     * Clear all data from local storage
     */
    clear: function() {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('Failed to clear localStorage:', error);
            return false;
        }
    }
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Memory Server MCP WebUI initialized');
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+S or Cmd+S to save (if on create/edit page)
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            const form = document.querySelector('#createForm, #editForm');
            if (form) {
                e.preventDefault();
                form.dispatchEvent(new Event('submit'));
            }
        }
        
        // Escape to cancel/close modals
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
    });
    
    // Add global error handler
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        Notifications.showError('予期しないエラーが発生しました。ページを更新してください。');
    });
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        Utils,
        ApiClient,
        LoadingManager,
        Notifications,
        FormValidator,
        Storage,
        CONFIG,
        STATE
    };
} else {
    // Make available globally
    window.MemoryApp = {
        Utils,
        ApiClient,
        LoadingManager,
        Notifications,
        FormValidator,
        Storage,
        CONFIG,
        STATE
    };
}