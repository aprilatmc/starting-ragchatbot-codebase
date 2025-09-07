// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, newChatButton, themeToggle;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    newChatButton = document.getElementById('newChatButton');
    themeToggle = document.getElementById('themeToggle');
    
    setupEventListeners();
    initializeTheme();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // New chat button
    newChatButton.addEventListener('click', startNewChat);
    
    // Theme toggle button
    themeToggle.addEventListener('click', toggleTheme);
    
    // Keyboard navigation for theme toggle
    themeToggle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleTheme();
        }
    });
    
    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();
        
        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;
    
    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        // Handle both old string format and new object format for backward compatibility
        const sourceLinks = sources.map(source => {
            if (typeof source === 'string') {
                // Old format - just display as text
                return source;
            } else if (source && source.text) {
                // New format - create clickable link if URL exists
                if (source.link) {
                    return `<a href="${escapeHtml(source.link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.text)}</a>`;
                } else {
                    return escapeHtml(source.text);
                }
            }
            return 'Unknown source';
        }).join(', ');
        
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${sourceLinks}</div>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

function startNewChat() {
    // Clear current session
    currentSessionId = null;
    
    // Clear chat messages
    chatMessages.innerHTML = '';
    
    // Add welcome message
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
    
    // Focus on input field
    chatInput.focus();
}

// Theme Functions
function initializeTheme() {
    // Check for saved theme preference, system preference, or default to 'dark'
    let savedTheme = localStorage.getItem('theme');
    
    // If no saved preference, detect system preference
    if (!savedTheme) {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
            savedTheme = 'light';
        } else {
            savedTheme = 'dark';
        }
    }
    
    applyTheme(savedTheme);
    
    // Listen for system theme changes
    if (window.matchMedia) {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: light)');
        const handleSystemThemeChange = (e) => {
            // Only auto-switch if user hasn't manually set a preference
            if (!localStorage.getItem('theme')) {
                applyTheme(e.matches ? 'light' : 'dark');
            }
        };
        
        // Use modern addEventListener if available, fallback to addListener
        if (mediaQuery.addEventListener) {
            mediaQuery.addEventListener('change', handleSystemThemeChange);
        } else {
            mediaQuery.addListener(handleSystemThemeChange);
        }
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    // Prevent rapid clicking during transition
    if (document.body.classList.contains('theme-transitioning')) {
        return;
    }
    
    // Add transition class for smooth theme switching
    document.body.classList.add('theme-transitioning');
    
    // Add visual feedback to button
    if (themeToggle) {
        themeToggle.style.transform = 'scale(0.9)';
        themeToggle.disabled = true;
    }
    
    // Apply the new theme
    applyTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Remove transition class and restore button after animation completes
    setTimeout(() => {
        document.body.classList.remove('theme-transitioning');
        if (themeToggle) {
            themeToggle.style.transform = '';
            themeToggle.disabled = false;
        }
    }, 300);
}

function applyTheme(theme) {
    const root = document.documentElement;
    
    // Use requestAnimationFrame for smooth visual updates
    requestAnimationFrame(() => {
        // Set data-theme attribute instead of class
        root.setAttribute('data-theme', theme);
        
        // Also set on body for additional styling flexibility
        document.body.setAttribute('data-theme', theme);
        
        // Update aria-pressed attribute for accessibility
        if (themeToggle) {
            themeToggle.setAttribute('aria-pressed', theme === 'light');
            
            // Update button title for better user feedback
            themeToggle.setAttribute('title', 
                theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'
            );
            
            // Update aria-label for screen readers
            themeToggle.setAttribute('aria-label', 
                theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'
            );
        }
    });
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');
        
        const data = await response.json();
        console.log('Course data received:', data);
        
        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }
        
        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}