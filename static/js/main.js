// ==================== FIXED GLOBAL VARIABLES ====================

// REMOVED old conflicting variables and kept only the new state objects



let breathingState = {

    interval: null,

    phase: 'inhale',

    count: 4,

    isActive: false

};



let appState = {

    userRegistered: false,

    currentPage: 'home',

    modalsOpen: new Set()

};



// In-memory storage (replaces localStorage for artifact compatibility)

let memoryStorage = {};



// ==================== UTILITY FUNCTIONS ====================



/**

 * Show loading overlay with optional custom message

 */

function showLoading(message = 'Loading...') {

    const overlay = document.getElementById('loadingOverlay');

    if (overlay) {

        const text = overlay.querySelector('p');

        if (text) text.textContent = message;

        overlay.style.display = 'flex';

    }

}



/**

 * Hide loading overlay

 */

function hideLoading() {

    const overlay = document.getElementById('loadingOverlay');

    if (overlay) overlay.style.display = 'none';

}



/**

 * Show flash message - FIXED version

 */

function showMessage(message, type = 'info', duration = 5000) {

    const container = document.getElementById('flashMessages');

    if (!container) return;



    const messageDiv = document.createElement('div');

    messageDiv.className = `flash-message flash-${type}`;

    messageDiv.innerHTML = `

        <span>${message}</span>

        <button onclick="this.parentElement.remove()" style="background: none; border: none; font-size: 1.2rem; color: #666; cursor: pointer;">×</button>

    `;



    container.appendChild(messageDiv);



    // Auto-remove after duration

    setTimeout(() => {

        if (messageDiv && messageDiv.parentElement) {

            messageDiv.remove();

        }

    }, duration);

}



/**

 * Format date for display

 */

function formatDate(dateString) {

    const date = new Date(dateString);

    return date.toLocaleDateString('en-US', {

        year: 'numeric',

        month: 'short',

        day: 'numeric'

    });

}



/**

 * Format time for display

 */

function formatTime(dateString) {

    const date = new Date(dateString);

    return date.toLocaleTimeString('en-US', {

        hour: '2-digit',

        minute: '2-digit'

    });

}



/**

 * Debounce function to limit API calls

 */

function debounce(func, wait) {

    let timeout;

    return function executedFunction(...args) {

        const later = () => {

            clearTimeout(timeout);

            func(...args);

        };

        clearTimeout(timeout);

        timeout = setTimeout(later, wait);

    };

}



// ==================== EMERGENCY HELP FUNCTIONS - FIXED ====================



/**

 * Show emergency help modal - FIXED to prevent auto-start

 */

function showEmergencyHelp() {

    const modal = document.getElementById('emergencyModal');

    if (modal && !appState.modalsOpen.has('emergency')) {

        modal.style.display = 'block';

        document.body.style.overflow = 'hidden';

        appState.modalsOpen.add('emergency');



        console.log('Emergency help opened by user interaction');



        // Track emergency help usage (anonymous)

        fetch('/api/emergency-help', {

            method: 'POST',

            headers: { 'Content-Type': 'application/json' },

            body: JSON.stringify({ action: 'emergency_help_opened' })

        }).catch(() => {}); // Silent fail - analytics not critical

    }

}



/**

 * Hide emergency help modal - FIXED

 */

function hideEmergencyHelp() {

    const modal = document.getElementById('emergencyModal');

    if (modal) {

        modal.style.display = 'none';

        document.body.style.overflow = 'auto';

        appState.modalsOpen.delete('emergency');

    }

}



/**

 * Start breathing exercise - COMPLETELY FIXED

 */

function startBreathingExercise() {

    // Only start if not already active and triggered by user interaction

    if (breathingState.isActive) {

        console.log('Breathing exercise already active');

        return;

    }



    console.log('Starting breathing exercise via user click');



    hideEmergencyHelp();



    const modal = document.getElementById('breathingModal');

    if (modal) {

        modal.style.display = 'flex';

        document.body.style.overflow = 'hidden';

        appState.modalsOpen.add('breathing');



        // Reset and initialize breathing state

        breathingState.isActive = true;

        breathingState.phase = 'inhale';

        breathingState.count = 4;



        updateBreathingDisplay();



        // Clear any existing interval

        if (breathingState.interval) {

            clearInterval(breathingState.interval);

        }



        // Start breathing cycle

        breathingState.interval = setInterval(() => {

            if (!breathingState.isActive) {

                clearInterval(breathingState.interval);

                return;

            }



            breathingState.count--;



            if (breathingState.count <= 0) {

                // Switch phase

                breathingState.phase = breathingState.phase === 'inhale' ? 'exhale' : 'inhale';

                breathingState.count = 4;

            }



            updateBreathingDisplay();

        }, 1000);



        // Track breathing exercise usage

        fetch('/api/emergency-help', {

            method: 'POST',

            headers: { 'Content-Type': 'application/json' },

            body: JSON.stringify({ action: 'breathing_exercise_started' })

        }).catch(() => {});

    }

}



/**

 * Stop breathing exercise - FIXED

 */

function stopBreathingExercise() {

    console.log('Stopping breathing exercise');



    const modal = document.getElementById('breathingModal');

    if (modal) {

        modal.style.display = 'none';

        document.body.style.overflow = 'auto';

        appState.modalsOpen.delete('breathing');

    }



    // Clear breathing state

    breathingState.isActive = false;

    if (breathingState.interval) {

        clearInterval(breathingState.interval);

        breathingState.interval = null;

    }



    // Reset circle animation

    const circle = document.getElementById('breathingCircle');

    if (circle) {

        circle.classList.remove('inhale', 'exhale');

        circle.style.transform = '';

    }



    // Track completion

    fetch('/api/emergency-help', {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify({ action: 'breathing_exercise_completed' })

    }).catch(() => {});

}



/**

 * Update breathing exercise display - FIXED

 */

function updateBreathingDisplay() {

    if (!breathingState.isActive) return;



    const instruction = document.getElementById('breathingInstruction');

    const count = document.getElementById('breathingCount');

    const circle = document.getElementById('breathingCircle');



    if (instruction) {

        instruction.textContent = breathingState.phase === 'inhale' ? 'Breathe In' : 'Breathe Out';

    }



    if (count) {

        count.textContent = breathingState.count;

    }



    if (circle) {

        // Remove previous classes

        circle.classList.remove('inhale', 'exhale');

        // Add current phase class

        circle.classList.add(breathingState.phase);



        // Fallback for browsers that don't support CSS classes

        circle.style.transform = breathingState.phase === 'inhale'

            ? 'scale(1.2)'

            : 'scale(1)';

    }

}



// ==================== FORM VALIDATION - FIXED ====================



/**

 * Validate email format

 */

function isValidEmail(email) {

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    return emailRegex.test(email);

}



/**

 * Validate company ID format

 */

function isValidCompanyId(companyId) {

    // Company ID should be lowercase, alphanumeric, hyphens allowed

    const companyIdRegex = /^[a-z0-9-]+$/;

    return companyIdRegex.test(companyId) && companyId.length >= 3;

}



/**

 * Real-time form validation - FIXED

 */

function setupFormValidation() {

    const companyInput = document.getElementById('companyId');

    if (companyInput) {

        companyInput.addEventListener('input', function(e) {

            let value = e.target.value.toLowerCase()

                .replace(/\s+/g, '-')

                .replace(/[^a-z0-9-]/g, '');



            e.target.value = value;



            // Visual feedback

            if (value.length >= 3 && isValidCompanyId(value)) {

                e.target.style.borderColor = '#28a745';

            } else if (value.length > 0) {

                e.target.style.borderColor = '#dc3545';

            } else {

                e.target.style.borderColor = '#e9ecef';

            }

        });

    }

}



// ==================== MEMORY STORAGE HELPERS (replaces localStorage) ====================



/**

 * Save to memory storage (replaces localStorage for artifact compatibility)

 */

function saveToStorage(key, data) {

    try {

        memoryStorage[key] = JSON.stringify(data);

        return true;

    } catch (error) {

        console.warn('Memory storage error:', error);

        return false;

    }

}



/**

 * Load from memory storage (replaces localStorage)

 */

function loadFromStorage(key, defaultValue = null) {

    try {

        const item = memoryStorage[key];

        return item ? JSON.parse(item) : defaultValue;

    } catch (error) {

        console.warn('Memory storage read error:', error);

        return defaultValue;

    }

}



/**

 * Remove from memory storage

 */

function removeFromStorage(key) {

    try {

        delete memoryStorage[key];

        return true;

    } catch (error) {

        console.warn('Memory storage remove error:', error);

        return false;

    }

}



// ==================== API HELPERS ====================



/**

 * Generic API call wrapper with error handling

 */

async function apiCall(url, options = {}) {

    const defaultOptions = {

        headers: {

            'Content-Type': 'application/json',

        },

        ...options

    };



    try {

        const response = await fetch(url, defaultOptions);



        if (!response.ok) {

            throw new Error(`HTTP error! status: ${response.status}`);

        }



        const contentType = response.headers.get('content-type');

        if (contentType && contentType.indexOf('application/json') !== -1) {

            return await response.json();

        } else {

            return await response.text();

        }

    } catch (error) {

        console.error('API call failed:', error);

        throw error;

    }

}



/**

 * Submit user registration

 */

async function submitRegistration(formData) {

    showLoading('Creating your account...');



    try {

        const response = await apiCall('/register', {

            method: 'POST',

            body: JSON.stringify(formData)

        });



        if (response.success) {

            showMessage('Welcome to Bloom! Setting up your first check-in...', 'success');



            // Save some non-sensitive data for better UX

            saveToStorage('bloom_onboarded', true);

            saveToStorage('bloom_department', formData.department);



            // Redirect after short delay

            setTimeout(() => {

                window.location.href = response.redirect;

            }, 2000);

        } else {

            throw new Error(response.error || 'Registration failed');

        }

    } catch (error) {

        showMessage(error.message || 'Registration failed. Please try again.', 'error');

        throw error;

    } finally {

        hideLoading();

    }

}



// ==================== CHART HELPERS ====================



/**

 * Create simple line chart for wellness scores

 */

function createWellnessChart(canvasId, data) {

    const canvas = document.getElementById(canvasId);

    if (!canvas || !data || data.length === 0) return;



    const ctx = canvas.getContext('2d');

    const width = canvas.width = canvas.offsetWidth * 2; // Retina support

    const height = canvas.height = canvas.offsetHeight * 2;



    // Scale for retina displays

    canvas.style.width = canvas.offsetWidth + 'px';

    canvas.style.height = canvas.offsetHeight + 'px';

    ctx.scale(2, 2);



    const chartWidth = width / 2 - 80;

    const chartHeight = height / 2 - 80;

    const padding = 40;



    // Clear canvas

    ctx.clearRect(0, 0, width / 2, height / 2);



    // Setup

    const maxScore = Math.max(...data.map(d => d.score), 100);

    const minScore = Math.min(...data.map(d => d.score), 0);

    const scoreRange = maxScore - minScore || 100;



    // Draw axes

    ctx.strokeStyle = '#e9ecef';

    ctx.lineWidth = 1;



    // Y-axis

    ctx.beginPath();

    ctx.moveTo(padding, padding);

    ctx.lineTo(padding, chartHeight + padding);

    ctx.stroke();



    // X-axis

    ctx.beginPath();

    ctx.moveTo(padding, chartHeight + padding);

    ctx.lineTo(chartWidth + padding, chartHeight + padding);

    ctx.stroke();



    // Draw data line

    if (data.length > 1) {

        ctx.strokeStyle = '#667eea';

        ctx.lineWidth = 3;

        ctx.beginPath();



        data.forEach((point, index) => {

            const x = padding + (index * chartWidth) / (data.length - 1);

            const y = padding + chartHeight - ((point.score - minScore) * chartHeight) / scoreRange;



            if (index === 0) {

                ctx.moveTo(x, y);

            } else {

                ctx.lineTo(x, y);

            }

        });



        ctx.stroke();



        // Draw data points

        ctx.fillStyle = '#667eea';

        data.forEach((point, index) => {

            const x = padding + (index * chartWidth) / (data.length - 1);

            const y = padding + chartHeight - ((point.score - minScore) * chartHeight) / scoreRange;



            ctx.beginPath();

            ctx.arc(x, y, 4, 0, 2 * Math.PI);

            ctx.fill();

        });

    }



    // Add labels

    ctx.fillStyle = '#666';

    ctx.font = '12px -apple-system, BlinkMacSystemFont, sans-serif';

    ctx.textAlign = 'center';



    // X-axis labels (dates)

    data.forEach((point, index) => {

        if (index % Math.ceil(data.length / 5) === 0) { // Show max 5 labels

            const x = padding + (index * chartWidth) / (data.length - 1);

            const date = new Date(point.date);

            const label = (date.getMonth() + 1) + '/' + date.getDate();

            ctx.fillText(label, x, chartHeight + padding + 20);

        }

    });



    // Y-axis labels

    ctx.textAlign = 'right';

    for (let i = 0; i <= 4; i++) {

        const score = minScore + (scoreRange * i) / 4;

        const y = padding + chartHeight - (i * chartHeight) / 4;

        ctx.fillText(Math.round(score), padding - 10, y + 4);

    }

}



// ==================== ANIMATION HELPERS ====================



/**

 * Animate number counting up

 */

function animateNumber(element, start, end, duration = 1000) {

    if (!element) return;



    const startTime = performance.now();

    const range = end - start;



    function updateNumber(currentTime) {

        const elapsed = currentTime - startTime;

        const progress = Math.min(elapsed / duration, 1);



        // Easing function

        const easeOut = 1 - Math.pow(1 - progress, 3);

        const current = start + (range * easeOut);



        element.textContent = Math.round(current);



        if (progress < 1) {

            requestAnimationFrame(updateNumber);

        }

    }



    requestAnimationFrame(updateNumber);

}



/**

 * Fade in element

 */

function fadeIn(element, duration = 300) {

    if (!element) return;



    element.style.opacity = '0';

    element.style.display = 'block';



    let start = null;



    function animate(timestamp) {

        if (!start) start = timestamp;

        const progress = timestamp - start;

        const opacity = Math.min(progress / duration, 1);



        element.style.opacity = opacity;



        if (progress < duration) {

            requestAnimationFrame(animate);

        }

    }



    requestAnimationFrame(animate);

}



/**

 * Slide down element

 */

function slideDown(element, duration = 300) {

    if (!element) return;



    element.style.maxHeight = '0';

    element.style.overflow = 'hidden';

    element.style.display = 'block';



    const targetHeight = element.scrollHeight;

    let start = null;



    function animate(timestamp) {

        if (!start) start = timestamp;

        const progress = timestamp - start;

        const height = Math.min((progress / duration) * targetHeight, targetHeight);



        element.style.maxHeight = height + 'px';



        if (progress < duration) {

            requestAnimationFrame(animate);

        } else {

            element.style.maxHeight = 'none';

            element.style.overflow = 'visible';

        }

    }



    requestAnimationFrame(animate);

}



// ==================== EVENT LISTENERS - FIXED ====================



/**

 * Setup global event listeners - FIXED to prevent auto-triggers

 */

function setupEventListeners() {

    // Close modals when clicking outside - FIXED

    window.addEventListener('click', function(e) {

        const emergencyModal = document.getElementById('emergencyModal');

        const breathingModal = document.getElementById('breathingModal');



        // Only close if clicking directly on modal background, not on modal content

        if (e.target === emergencyModal) {

            hideEmergencyHelp();

        }



        if (e.target === breathingModal) {

            stopBreathingExercise();

        }

    });



    // Keyboard shortcuts - FIXED

    document.addEventListener('keydown', function(e) {

        // Escape key closes modals

        if (e.key === 'Escape') {

            if (appState.modalsOpen.has('breathing')) {

                stopBreathingExercise();

            }

            if (appState.modalsOpen.has('emergency')) {

                hideEmergencyHelp();

            }

        }



        // Alt + H opens emergency help (only if no modals open)

        if (e.altKey && e.key === 'h' && appState.modalsOpen.size === 0) {

            e.preventDefault();

            showEmergencyHelp();

        }

    });



    // Handle online/offline status

    window.addEventListener('online', function() {

        showMessage('Connection restored', 'success', 3000);

    });



    window.addEventListener('offline', function() {

        showMessage('Connection lost. Some features may not work.', 'warning', 5000);

    });



    // Auto-hide flash messages on scroll

    let scrollTimeout;

    window.addEventListener('scroll', function() {

        clearTimeout(scrollTimeout);

        scrollTimeout = setTimeout(() => {

            const messages = document.querySelectorAll('.flash-message');

            messages.forEach(msg => {

                if (msg.getBoundingClientRect().top < 0) {

                    msg.style.opacity = '0.5';

                }

            });

        }, 100);

    });



    // REMOVED auto-trigger events that could cause issues

}



// ==================== INITIALIZATION - FIXED ====================



/**

 * Initialize the application - FIXED to prevent auto-starts

 */

function initializeApp() {

    console.log('🌸 Initializing iBloom app...');



    // Reset all state

    breathingState.isActive = false;

    appState.modalsOpen.clear();



    // Clear any existing intervals

    if (breathingState.interval) {

        clearInterval(breathingState.interval);

        breathingState.interval = null;

    }



    // Ensure all modals are hidden

    const modals = document.querySelectorAll('.modal');

    modals.forEach(modal => {

        modal.style.display = 'none';

    });



    // Reset body overflow

    document.body.style.overflow = 'auto';



    // Setup form validation

    setupFormValidation();



    // Setup event listeners

    setupEventListeners();



    // Check if user is returning

    const isOnboarded = loadFromStorage('bloom_onboarded', false);

    if (isOnboarded) {

        console.log('Welcome back to Bloom!');

    }



    // Initialize page-specific functionality

    const currentPage = window.location.pathname;



    if (currentPage === '/') {

        initializeLandingPage();

    } else if (currentPage === '/questionnaire') {

        initializeQuestionnairePage();

    } else if (currentPage === '/dashboard') {

        initializeDashboardPage();

    }



    console.log('✅ Bloom app initialized successfully - no auto-triggers');

}



/**

 * Initialize landing page

 */

function initializeLandingPage() {

    // Auto-focus company ID input after a short delay

    setTimeout(() => {

        const companyInput = document.getElementById('companyId');

        if (companyInput) {

            companyInput.focus();

        }

    }, 500);



    // Pre-fill department if returning user

    const savedDepartment = loadFromStorage('bloom_department');

    const departmentSelect = document.getElementById('department');

    if (savedDepartment && departmentSelect) {

        departmentSelect.value = savedDepartment;

    }

}



/**

 * Initialize questionnaire page

 */

function initializeQuestionnairePage() {

    // Add auto-save for partially completed responses

    let autoSaveTimeout;

    document.addEventListener('input', function() {

        clearTimeout(autoSaveTimeout);

        autoSaveTimeout = setTimeout(() => {

            // Auto-save current progress (non-critical)

            const currentResponses = window.responses || [];

            saveToStorage('bloom_temp_responses', {

                responses: currentResponses,

                timestamp: Date.now()

            });

        }, 2000);

    });



    // Clear old temp data on load

    const tempData = loadFromStorage('bloom_temp_responses');

    if (tempData && Date.now() - tempData.timestamp > 24 * 60 * 60 * 1000) {

        removeFromStorage('bloom_temp_responses');

    }

}



/**

 * Initialize dashboard page

 */

function initializeDashboardPage() {

    // Load and display user data

    loadUserDashboardData();

}



/**

 * Load user dashboard data

 */

async function loadUserDashboardData() {

    try {

        showLoading('Loading your wellness data...');



        const data = await apiCall('/api/user-data');



        if (data.chart_data && data.chart_data.length > 0) {

            // Create wellness chart

            createWellnessChart('wellnessChart', data.chart_data);



            // Animate stats

            const avgScoreElement = document.getElementById('avgScore');

            if (avgScoreElement) {

                animateNumber(avgScoreElement, 0, Math.round(data.avg_score));

            }



            const totalResponsesElement = document.getElementById('totalResponses');

            if (totalResponsesElement) {

                animateNumber(totalResponsesElement, 0, data.total_responses);

            }

        }



        // Display latest analysis

        if (data.latest_analysis) {

            displayLatestAnalysis(data.latest_analysis);

        }



    } catch (error) {

        console.error('Failed to load dashboard data:', error);

        showMessage('Failed to load dashboard data', 'error');

    } finally {

        hideLoading();

    }

}



/**

 * Display latest analysis on dashboard

 */

function displayLatestAnalysis(analysis) {

    const container = document.getElementById('latestAnalysis');

    if (!container || !analysis) return;



    const recommendations = analysis.recommendations || [];

    const concerns = analysis.concerns || [];



    let html = `

        <div class="latest-analysis">

            <h3>Latest Check-in Insights</h3>

    `;



    if (concerns.length > 0) {

        html += `

            <div class="concerns-summary">

                <h4>Areas of Attention:</h4>

                <ul>

                    ${concerns.map(concern => `<li>${concern}</li>`).join('')}

                </ul>

            </div>

        `;

    }



    if (recommendations.length > 0) {

        html += `

            <div class="recommendations-summary">

                <h4>Recommended Actions:</h4>

                <ul>

                    ${recommendations.map(rec => {

            const text = rec.action || rec.title || rec.habit || rec;

            return `<li>${text}</li>`;

        }).join('')}

                </ul>

            </div>

        `;

    }



    html += '</div>';

    container.innerHTML = html;



    // Animate in

    fadeIn(container);

}



// ==================== START APPLICATION - FIXED ====================



// Initialize when DOM is ready - ONLY ONCE

document.addEventListener('DOMContentLoaded', function() {

    // Prevent multiple initializations

    if (window.bloomInitialized) {

        console.log('iBloom already initialized, skipping...');

        return;

    }



    window.bloomInitialized = true;

    initializeApp();

});



// Make functions available globally for onclick handlers

window.showEmergencyHelp = showEmergencyHelp;

window.hideEmergencyHelp = hideEmergencyHelp;

window.startBreathingExercise = startBreathingExercise;

window.stopBreathingExercise = stopBreathingExercise;

window.showMessage = showMessage;

window.showLoading = showLoading;

window.hideLoading = hideLoading;