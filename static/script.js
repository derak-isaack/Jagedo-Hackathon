// Construction Platform JavaScript

// Global utility functions
const ConstructPlatform = {
    // Initialize the application
    init() {
        this.setupEventListeners();
        this.initializeComponents();
        this.setupFormValidation();
        this.setupNotifications();
    },

    // Set up global event listeners
    setupEventListeners() {
        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });

        // Auto-hide alerts after 5 seconds
        document.querySelectorAll('.alert').forEach(alert => {
            if (alert.classList.contains('alert-success') || alert.classList.contains('alert-info')) {
                setTimeout(() => {
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                }, 5000);
            }
        });

        // Tooltip initialization
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Popover initialization
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    },

    // Initialize components
    initializeComponents() {
        this.setupSearchFunctionality();
        this.setupFileUpload();
        this.setupCounters();
        this.addAnimationOnScroll();
    },

    // Set up search functionality
    setupSearchFunctionality() {
        const searchInputs = document.querySelectorAll('.search-input');
        searchInputs.forEach(input => {
            input.addEventListener('input', function() {
                const searchTerm = this.value.toLowerCase();
                const targetSelector = this.getAttribute('data-target');
                const targets = document.querySelectorAll(targetSelector);
                
                targets.forEach(target => {
                    const text = target.textContent.toLowerCase();
                    if (text.includes(searchTerm)) {
                        target.style.display = '';
                    } else {
                        target.style.display = 'none';
                    }
                });
            });
        });
    },

    // Set up file upload with progress
    setupFileUpload() {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            input.addEventListener('change', function() {
                const fileName = this.files[0]?.name;
                if (fileName) {
                    const label = this.nextElementSibling || this.previousElementSibling;
                    if (label && label.classList.contains('form-label')) {
                        label.textContent = `Selected: ${fileName}`;
                    }
                }
            });
        });
    },

    // Set up animated counters
    setupCounters() {
        const counters = document.querySelectorAll('.counter');
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        counters.forEach(counter => observer.observe(counter));
    },

    // Animate counter numbers
    animateCounter(element) {
        const target = parseInt(element.textContent);
        const duration = 2000;
        const step = target / (duration / 16);
        let current = 0;

        const timer = setInterval(() => {
            current += step;
            element.textContent = Math.floor(current);
            
            if (current >= target) {
                element.textContent = target;
                clearInterval(timer);
            }
        }, 16);
    },

    // Add animation on scroll
    addAnimationOnScroll() {
        const animatedElements = document.querySelectorAll('.fade-in, .slide-in-left, .slide-in-right');
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateX(0) translateY(0)';
                }
            });
        }, observerOptions);

        animatedElements.forEach(element => {
            element.style.opacity = '0';
            observer.observe(element);
        });
    },

    // Set up form validation
    setupFormValidation() {
        const forms = document.querySelectorAll('.needs-validation');
        forms.forEach(form => {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });

        // Real-time validation
        const inputs = document.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                this.classList.add('was-validated');
            });
        });
    },

    // Set up notifications
    setupNotifications() {
        // Check for new notifications every 30 seconds
        if (document.querySelector('.navbar')) {
            setInterval(() => {
                this.checkNotifications();
            }, 30000);
        }
    },

    // Check for new notifications (placeholder)
    checkNotifications() {
        // This would typically make an AJAX call to check for new notifications
        console.log('Checking for notifications...');
    },

    // Utility functions
    utils: {
        // Show loading state
        showLoading(element, text = 'Loading...') {
            const originalContent = element.innerHTML;
            element.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${text}`;
            element.disabled = true;
            return originalContent;
        },

        // Hide loading state
        hideLoading(element, originalContent) {
            element.innerHTML = originalContent;
            element.disabled = false;
        },

        // Format currency
        formatCurrency(amount) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
            }).format(amount);
        },

        // Format date
        formatDate(date) {
            return new Intl.DateTimeFormat('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            }).format(new Date(date));
        },

        // Show toast notification
        showToast(message, type = 'info') {
            const toastContainer = document.querySelector('.toast-container') || this.createToastContainer();
            const toast = this.createToast(message, type);
            toastContainer.appendChild(toast);
            
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
            
            toast.addEventListener('hidden.bs.toast', () => {
                toast.remove();
            });
        },

        // Create toast container
        createToastContainer() {
            const container = document.createElement('div');
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1055';
            document.body.appendChild(container);
            return container;
        },

        // Create toast element
        createToast(message, type) {
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.setAttribute('role', 'alert');
            
            const iconClass = {
                'success': 'fa-check-circle text-success',
                'error': 'fa-exclamation-circle text-danger',
                'warning': 'fa-exclamation-triangle text-warning',
                'info': 'fa-info-circle text-info'
            }[type] || 'fa-info-circle text-info';
            
            toast.innerHTML = `
                <div class="toast-header">
                    <i class="fas ${iconClass} me-2"></i>
                    <strong class="me-auto">Construction Platform</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            `;
            
            return toast;
        },

        // Debounce function
        debounce(func, wait) {
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

        // Throttle function
        throttle(func, limit) {
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
        }
    }
};

// Job-specific functionality
const JobManager = {
    // Auto-save draft functionality
    setupAutoSave() {
        const form = document.querySelector('#jobForm');
        if (!form) return;

        const inputs = form.querySelectorAll('input, textarea, select');
        const debouncedSave = ConstructPlatform.utils.debounce(this.saveDraft, 2000);

        inputs.forEach(input => {
            input.addEventListener('input', debouncedSave);
        });
    },

    // Save draft to localStorage
    saveDraft() {
        const form = document.querySelector('#jobForm');
        if (!form) return;

        const formData = new FormData(form);
        const draft = {};
        for (let [key, value] of formData.entries()) {
            draft[key] = value;
        }

        localStorage.setItem('jobDraft', JSON.stringify(draft));
        console.log('Draft saved');
    },

    // Load draft from localStorage
    loadDraft() {
        const draft = localStorage.getItem('jobDraft');
        if (!draft) return;

        const draftData = JSON.parse(draft);
        Object.keys(draftData).forEach(key => {
            const input = document.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = draftData[key];
            }
        });
    },

    // Clear draft
    clearDraft() {
        localStorage.removeItem('jobDraft');
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    ConstructPlatform.init();
    JobManager.setupAutoSave();
    JobManager.loadDraft();
});

// Handle form submissions
document.addEventListener('submit', function(e) {
    if (e.target.id === 'jobForm') {
        JobManager.clearDraft();
    }
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'hidden') {
        JobManager.saveDraft();
    }
});

// Export for global use
window.ConstructPlatform = ConstructPlatform;
window.JobManager = JobManager;
