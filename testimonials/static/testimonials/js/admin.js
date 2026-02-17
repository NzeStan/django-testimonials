/**
 * Admin JavaScript for Django Testimonials
 * Optimized for performance and better UX
 */

(function($) {
    'use strict';

    // === PERFORMANCE OPTIMIZATIONS ===
    
    // Use passive event listeners for better scroll performance
    const passiveSupported = (function() {
        let passiveSupported = false;
        try {
            const options = {
                get passive() {
                    passiveSupported = true;
                    return false;
                }
            };
            window.addEventListener('test', null, options);
            window.removeEventListener('test', null, options);
        } catch (err) {
            passiveSupported = false;
        }
        return passiveSupported;
    })();

    // Debounce function for performance
    function debounce(func, wait, immediate) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func.apply(this, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(this, args);
        };
    }

    // Throttle function for scroll events
    function throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // === STAR RATING WIDGET ===
    
    function initStarRating() {
        const starContainers = document.querySelectorAll('.star-rating-container');
        
        starContainers.forEach(container => {
            const stars = container.querySelectorAll('.star-rating-label');
            const inputs = container.querySelectorAll('input[type="radio"]');
            
            // Optimize with event delegation
            container.addEventListener('click', function(e) {
                if (e.target.classList.contains('star-rating-label')) {
                    const clickedInput = e.target.previousElementSibling;
                    if (clickedInput && clickedInput.type === 'radio') {
                        clickedInput.checked = true;
                        updateStarDisplay(container, clickedInput.value);
                    }
                }
            });
            
            // Hover effects
            container.addEventListener('mouseover', function(e) {
                if (e.target.classList.contains('star-rating-label')) {
                    const hoverInput = e.target.previousElementSibling;
                    if (hoverInput && hoverInput.type === 'radio') {
                        highlightStars(container, hoverInput.value);
                    }
                }
            });
            
            container.addEventListener('mouseout', function() {
                const checkedInput = container.querySelector('input[type="radio"]:checked');
                const value = checkedInput ? checkedInput.value : 0;
                updateStarDisplay(container, value);
            });
            
            // Initialize display
            const checkedInput = container.querySelector('input[type="radio"]:checked');
            if (checkedInput) {
                updateStarDisplay(container, checkedInput.value);
            }
        });
    }
    
    function updateStarDisplay(container, rating) {
        const labels = container.querySelectorAll('.star-rating-label');
        labels.forEach((label, index) => {
            if (index < rating) {
                label.textContent = '★';
                label.style.color = '#ffc107';
            } else {
                label.textContent = '☆';
                label.style.color = '#dee2e6';
            }
        });
    }
    
    function highlightStars(container, rating) {
        const labels = container.querySelectorAll('.star-rating-label');
        labels.forEach((label, index) => {
            if (index < rating) {
                label.style.color = '#ffc107';
            } else {
                label.style.color = '#dee2e6';
            }
        });
    }

    // === BULK ACTIONS ===
    
    function initBulkActions() {
        const actionSelect = document.querySelector('select[name="action"]');
        const goButton = document.querySelector('button[title="Run the selected action"]');
        
        if (!actionSelect || !goButton) return;
        
        const originalSubmit = goButton.onclick;
        
        goButton.onclick = function(e) {
            const selectedAction = actionSelect.value;
            const selectedItems = document.querySelectorAll('input[name="_selected_action"]:checked');
            
            if (selectedItems.length === 0) {
                alert('Please select at least one testimonial.');
                e.preventDefault();
                return false;
            }
            
            // Special handling for reject action
            if (selectedAction === 'reject_testimonials') {
                e.preventDefault();
                showRejectDialog(selectedItems);
                return false;
            }
            
            // Confirmation for other bulk actions
            if (selectedAction && selectedAction !== '---------') {
                const actionText = actionSelect.options[actionSelect.selectedIndex].text;
                const itemCount = selectedItems.length;
                const confirmMessage = `Are you sure you want to ${actionText.toLowerCase()} ${itemCount} testimonial(s)?`;
                
                if (!confirm(confirmMessage)) {
                    e.preventDefault();
                    return false;
                }
                
                // Show loading state
                showLoadingState(goButton);
            }
            
            // Call original submit if exists
            if (originalSubmit) {
                return originalSubmit.call(this, e);
            }
        };
    }
    
    function showRejectDialog(selectedItems) {
        const dialog = createRejectDialog();
        document.body.appendChild(dialog);
        
        // Focus on reason textarea
        const reasonTextarea = dialog.querySelector('#rejection_reason');
        setTimeout(() => reasonTextarea.focus(), 100);
    }
    
    function createRejectDialog() {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        
        const dialog = document.createElement('div');
        dialog.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 8px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        `;
        
        dialog.innerHTML = `
            <h3 style="margin-top: 0; color: #dc3545;">Reject Testimonials</h3>
            <p>Please provide a reason for rejecting the selected testimonials:</p>
            <form id="reject-form">
                <textarea id="rejection_reason" name="rejection_reason" 
                         style="width: 100%; height: 100px; padding: 10px; border: 1px solid #ddd; border-radius: 4px;"
                         placeholder="Enter rejection reason..." required></textarea>
                <div style="margin-top: 15px; text-align: right;">
                    <button type="button" id="cancel-reject" 
                            style="padding: 8px 16px; margin-right: 10px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        Cancel
                    </button>
                    <button type="submit" 
                            style="padding: 8px 16px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        Reject Testimonials
                    </button>
                </div>
            </form>
        `;
        
        overlay.appendChild(dialog);
        
        // Event handlers
        dialog.querySelector('#cancel-reject').onclick = () => {
            document.body.removeChild(overlay);
        };
        
        dialog.querySelector('#reject-form').onsubmit = (e) => {
            e.preventDefault();
            const reason = dialog.querySelector('#rejection_reason').value.trim();
            
            if (!reason) {
                alert('Please provide a rejection reason.');
                return;
            }
            
            // Create hidden form and submit
            submitRejectForm(reason);
            document.body.removeChild(overlay);
        };
        
        // Close on overlay click
        overlay.onclick = (e) => {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
            }
        };
        
        // Close on Escape key
        document.addEventListener('keydown', function escHandler(e) {
            if (e.key === 'Escape') {
                document.body.removeChild(overlay);
                document.removeEventListener('keydown', escHandler);
            }
        });
        
        return overlay;
    }
    
    function submitRejectForm(rejectionReason) {
        const form = document.querySelector('#changelist-form');
        if (!form) return;
        
        // Add rejection reason to form
        const reasonInput = document.createElement('input');
        reasonInput.type = 'hidden';
        reasonInput.name = 'rejection_reason';
        reasonInput.value = rejectionReason;
        form.appendChild(reasonInput);
        
        // Set action
        const actionSelect = form.querySelector('select[name="action"]');
        if (actionSelect) {
            actionSelect.value = 'reject_testimonials';
        }
        
        // Submit form
        form.submit();
    }
    
    function showLoadingState(button) {
        const originalText = button.textContent;
        button.disabled = true;
        button.innerHTML = '<span class="loading-spinner"></span> Processing...';
        
        // Restore button after timeout (fallback)
        setTimeout(() => {
            button.disabled = false;
            button.textContent = originalText;
        }, 30000);
    }

    // === MEDIA PREVIEW ===
    
    function initMediaPreview() {
        const mediaInputs = document.querySelectorAll('input[type="file"]');
        
        mediaInputs.forEach(input => {
            input.addEventListener('change', function(e) {
                previewFile(this, e.target.files[0]);
            });
        });
    }
    
    function previewFile(input, file) {
        if (!file) return;
        
        const preview = getOrCreatePreview(input);
        const fileType = file.type.split('/')[0];
        
        const reader = new FileReader();
        reader.onload = function(e) {
            const result = e.target.result;
            
            switch (fileType) {
                case 'image':
                    preview.innerHTML = `<img src="${result}" class="media-preview" alt="Preview">`;
                    break;
                case 'video':
                    preview.innerHTML = `<video src="${result}" class="media-preview" controls></video>`;
                    break;
                case 'audio':
                    preview.innerHTML = `<audio src="${result}" class="media-preview" controls></audio>`;
                    break;
                default:
                    preview.innerHTML = `<p>📄 ${file.name} (${formatFileSize(file.size)})</p>`;
            }
        };
        
        reader.readAsDataURL(file);
    }
    
    function getOrCreatePreview(input) {
        let preview = input.parentNode.querySelector('.file-preview');
        
        if (!preview) {
            preview = document.createElement('div');
            preview.className = 'file-preview';
            preview.style.marginTop = '10px';
            input.parentNode.appendChild(preview);
        }
        
        return preview;
    }
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // === AJAX SEARCH ===
    
    function initAjaxSearch() {
        const searchInput = document.querySelector('#searchbar');
        if (!searchInput) return;
        
        const debouncedSearch = debounce(performSearch, 300);
        
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value.trim();
            if (query.length >= 3 || query.length === 0) {
                debouncedSearch(query);
            }
        });
    }
    
    function performSearch(query) {
        // This would implement AJAX search functionality
        // For now, it's a placeholder
        console.log('Performing search for:', query);
    }

    // === RESPONSIVE TABLES ===
    
    function initResponsiveTables() {
        const tables = document.querySelectorAll('.results table');
        
        tables.forEach(table => {
            makeTableResponsive(table);
        });
    }
    
    function makeTableResponsive(table) {
        // Add horizontal scroll for mobile
        if (window.innerWidth < 768) {
            table.style.display = 'block';
            table.style.overflowX = 'auto';
            table.style.whiteSpace = 'nowrap';
        }
        
        // Add resize listener
        const resizeHandler = throttle(() => {
            if (window.innerWidth < 768) {
                table.style.display = 'block';
                table.style.overflowX = 'auto';
                table.style.whiteSpace = 'nowrap';
            } else {
                table.style.display = '';
                table.style.overflowX = '';
                table.style.whiteSpace = '';
            }
        }, 250);
        
        window.addEventListener('resize', resizeHandler, passiveSupported ? { passive: true } : false);
    }

    // === KEYBOARD SHORTCUTS ===
    
    function initKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + A to select all checkboxes
            if ((e.ctrlKey || e.metaKey) && e.key === 'a' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
                toggleAllCheckboxes(true);
            }
            
            // Ctrl/Cmd + D to deselect all checkboxes
            if ((e.ctrlKey || e.metaKey) && e.key === 'd' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
                toggleAllCheckboxes(false);
            }
            
            // Escape to close dialogs
            if (e.key === 'Escape') {
                closeAllDialogs();
            }
        });
    }
    
    function toggleAllCheckboxes(checked) {
        const checkboxes = document.querySelectorAll('input[name="_selected_action"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = checked;
        });
        
        // Update select all checkbox
        const selectAllCheckbox = document.querySelector('#action-toggle');
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = checked;
        }
    }
    
    function closeAllDialogs() {
        const overlays = document.querySelectorAll('.loading-overlay');
        overlays.forEach(overlay => {
            if (overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
        });
    }

    // === FORM VALIDATION ===
    
    function initFormValidation() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!validateForm(this)) {
                    e.preventDefault();
                    return false;
                }
            });
        });
    }
    
    function validateForm(form) {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                showFieldError(field, 'This field is required.');
                isValid = false;
            } else {
                clearFieldError(field);
            }
        });
        
        // Custom validation for testimonial content
        const contentFields = form.querySelectorAll('.testimonial-content');
        contentFields.forEach(field => {
            if (field.value.trim().length < 10) {
                showFieldError(field, 'Content must be at least 10 characters long.');
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    function showFieldError(field, message) {
        clearFieldError(field);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.style.cssText = 'color: #dc3545; font-size: 12px; margin-top: 4px;';
        errorDiv.textContent = message;
        
        field.parentNode.appendChild(errorDiv);
        field.style.borderColor = '#dc3545';
    }
    
    function clearFieldError(field) {
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        field.style.borderColor = '';
    }

    // === PERFORMANCE MONITORING ===
    
    function initPerformanceMonitoring() {
        // Monitor page load time
        window.addEventListener('load', function() {
            setTimeout(() => {
                if (window.performance && window.performance.timing) {
                    const loadTime = window.performance.timing.loadEventEnd - window.performance.timing.navigationStart;
                    console.log('Page load time:', loadTime + 'ms');
                    
                    // Send to analytics if configured
                    if (window.gtag) {
                        gtag('event', 'page_load_time', {
                            value: loadTime,
                            custom_parameter: 'testimonials_admin'
                        });
                    }
                }
            }, 0);
        });
        
        // Monitor AJAX performance
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            const start = performance.now();
            return originalFetch.apply(this, args).then(response => {
                const end = performance.now();
                console.log(`AJAX request took ${end - start}ms`);
                return response;
            });
        };
    }

    // === ACCESSIBILITY ENHANCEMENTS ===
    
    function initAccessibility() {
        // Add ARIA labels to buttons without text
        const iconButtons = document.querySelectorAll('button:empty, input[type="submit"]:empty');
        iconButtons.forEach(button => {
            if (!button.getAttribute('aria-label')) {
                button.setAttribute('aria-label', 'Action button');
            }
        });
        
        // Improve focus management
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });
        
        document.addEventListener('mousedown', function() {
            document.body.classList.remove('keyboard-navigation');
        });
        
        // Add skip links
        addSkipLinks();
    }
    
    function addSkipLinks() {
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.textContent = 'Skip to main content';
        skipLink.style.cssText = `
            position: absolute;
            top: -40px;
            left: 6px;
            background: #000;
            color: #fff;
            padding: 8px;
            text-decoration: none;
            z-index: 10000;
        `;
        
        skipLink.addEventListener('focus', function() {
            this.style.top = '6px';
        });
        
        skipLink.addEventListener('blur', function() {
            this.style.top = '-40px';
        });
        
        document.body.insertBefore(skipLink, document.body.firstChild);
    }

    // === INITIALIZATION ===
    
    function init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeComponents);
        } else {
            initializeComponents();
        }
    }
    
    function initializeComponents() {
        try {
            initStarRating();
            initBulkActions();
            initMediaPreview();
            initAjaxSearch();
            initResponsiveTables();
            initKeyboardShortcuts();
            initFormValidation();
            initPerformanceMonitoring();
            initAccessibility();
            
            console.log('Testimonials admin JS initialized successfully');
        } catch (error) {
            console.error('Error initializing testimonials admin JS:', error);
        }
    }
    
    // Start initialization
    init();

})(django.jQuery || jQuery);

// === CSS FOR KEYBOARD NAVIGATION ===
// Add to document head
(function() {
    const style = document.createElement('style');
    style.textContent = `
        body:not(.keyboard-navigation) *:focus {
            outline: none;
        }
        
        .keyboard-navigation *:focus {
            outline: 2px solid #0066cc;
            outline-offset: 2px;
        }
    `;
    document.head.appendChild(style);
})();