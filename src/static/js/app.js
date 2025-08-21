document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('.date-form');
    
    forms.forEach(form => {
        form.addEventListener('submit', handleDateSubmit);
    });
    
    // Add ignore button handlers
    const ignoreButtons = document.querySelectorAll('.ignore-btn');
    ignoreButtons.forEach(button => {
        button.addEventListener('click', handleIgnoreClick);
    });
    
    // Add batch date form handlers
    const batchDateForms = document.querySelectorAll('.batch-date-form');
    batchDateForms.forEach(form => {
        form.addEventListener('submit', handleBatchDateSubmit);
    });
    
    // Initialize modal functionality
    initializeModal();
    
    // Initialize search functionality
    initializeSearch();
});

async function handleDateSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const photoContainer = form.closest('.photo-pair');
    const baseName = photoContainer.dataset.baseName;
    const dateInput = form.querySelector('input[type="date"]');
    const submitButton = form.querySelector('button');
    const statusMessage = photoContainer.querySelector('.status-message');
    
    const selectedDate = dateInput.value;
    
    if (!selectedDate) {
        showStatus(statusMessage, 'Please select a date', 'error');
        return;
    }
    
    // Disable form during submission
    submitButton.disabled = true;
    dateInput.disabled = true;
    showStatus(statusMessage, 'Updating photo dates...', 'loading');
    
    try {
        const response = await fetch('/update_date', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                base_name: baseName,
                date: selectedDate
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showStatus(statusMessage, result.message, 'success');
            
            // Hide the photo pair after successful update
            setTimeout(() => {
                photoContainer.style.transition = 'opacity 0.5s ease-out';
                photoContainer.style.opacity = '0';
                setTimeout(() => {
                    photoContainer.remove();
                    checkIfAllPhotosProcessed();
                }, 500);
            }, 2000);
            
        } else {
            showStatus(statusMessage, `Error: ${result.message}`, 'error');
            
            // Show detailed results if available
            if (result.results && result.results.length > 0) {
                const details = result.results
                    .map(r => `${r.file}: ${r.success ? 'Success' : 'Failed - ' + r.message}`)
                    .join('<br>');
                statusMessage.innerHTML += `<br><small>${details}</small>`;
            }
        }
        
    } catch (error) {
        console.error('Error updating date:', error);
        showStatus(statusMessage, 'Network error. Please try again.', 'error');
    } finally {
        // Re-enable form
        submitButton.disabled = false;
        dateInput.disabled = false;
    }
}

async function handleIgnoreClick(event) {
    event.preventDefault();
    
    const button = event.target;
    const photoContainer = button.closest('.photo-pair');
    const baseName = photoContainer.dataset.baseName;
    const statusMessage = photoContainer.querySelector('.status-message');
    
    // Confirm with user
    if (!confirm(`Are you sure you want to mark all photos for ${baseName} as unknown date? This will set the date to 1900-01-01.`)) {
        return;
    }
    
    // Disable button during request
    button.disabled = true;
    button.textContent = 'Processing...';
    showStatus(statusMessage, 'Setting unknown date...', 'loading');
    
    try {
        const response = await fetch('/update_date', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                base_name: baseName,
                date: '1900-01-01'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showStatus(statusMessage, result.message, 'success');
            
            // Hide the photo pair after successful update
            setTimeout(() => {
                photoContainer.style.transition = 'opacity 0.5s ease-out';
                photoContainer.style.opacity = '0';
                setTimeout(() => {
                    photoContainer.remove();
                    checkIfAllPhotosProcessed();
                }, 500);
            }, 2000);
            
        } else {
            showStatus(statusMessage, `Error: ${result.message}`, 'error');
            
            // Show detailed results if available
            if (result.results && result.results.length > 0) {
                const details = result.results
                    .map(r => `${r.file}: ${r.success ? 'Success' : 'Failed - ' + r.message}`)
                    .join('<br>');
                statusMessage.innerHTML += `<br><small>${details}</small>`;
            }
            
            button.disabled = false;
            button.textContent = 'Unknown';
        }
        
    } catch (error) {
        console.error('Error setting unknown date:', error);
        showStatus(statusMessage, 'Network error. Please try again.', 'error');
        button.disabled = false;
        button.textContent = 'Unknown';
    }
}

async function handleBatchDateSubmit(event) {
    event.preventDefault();
    
    console.log('Batch date submit triggered');
    
    const form = event.target;
    const groupSection = form.closest('.similarity-group');
    const dateInput = form.querySelector('input[type="date"]');
    const submitButton = form.querySelector('button[type="submit"]');
    const batchDateSection = form.closest('.batch-date-section');
    const batchStatusMessage = batchDateSection.querySelector('.batch-status-message');
    const groupId = submitButton.dataset.groupId;
    
    console.log('Elements found:', {
        form: !!form,
        groupSection: !!groupSection,
        dateInput: !!dateInput,
        submitButton: !!submitButton,
        batchDateSection: !!batchDateSection,
        batchStatusMessage: !!batchStatusMessage,
        groupId: groupId
    });
    
    // Find all photo pairs in this group
    const photoPairs = groupSection.querySelectorAll('.photo-pair');
    
    console.log('Found photo pairs:', photoPairs.length);
    
    if (photoPairs.length === 0) {
        if (batchStatusMessage) {
            showStatus(batchStatusMessage, 'No photos found in this group', 'error');
        } else {
            alert('No photos found in this group');
        }
        return;
    }
    
    const selectedDate = dateInput.value;
    console.log('Selected date:', selectedDate);
    
    if (!selectedDate) {
        if (batchStatusMessage) {
            showStatus(batchStatusMessage, 'Please select a date', 'error');
        } else {
            alert('Please select a date');
        }
        return;
    }
    
    // Disable form during batch update
    submitButton.disabled = true;
    dateInput.disabled = true;
    const originalButtonText = submitButton.textContent;
    submitButton.textContent = 'Updating...';
    if (batchStatusMessage) {
        showStatus(batchStatusMessage, `Updating ${photoPairs.length} photo sets...`, 'loading');
    }
    
    let successCount = 0;
    let errorCount = 0;
    
    // Update each photo pair in the group
    for (const photoPair of photoPairs) {
        const baseName = photoPair.dataset.baseName;
        const statusMessage = photoPair.querySelector('.status-message');
        
        try {
            showStatus(statusMessage, 'Updating...', 'loading');
            
            const response = await fetch('/update_date', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    base_name: baseName,
                    date: selectedDate
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                showStatus(statusMessage, 'Updated successfully', 'success');
                successCount++;
                
                // Hide the photo pair after successful update
                setTimeout(() => {
                    photoPair.style.transition = 'opacity 0.5s ease-out';
                    photoPair.style.opacity = '0';
                    setTimeout(() => {
                        photoPair.remove();
                    }, 500);
                }, 1000);
                
            } else {
                showStatus(statusMessage, `Error: ${result.message}`, 'error');
                errorCount++;
            }
            
        } catch (error) {
            console.error('Error updating date for', baseName, ':', error);
            showStatus(statusMessage, 'Network error', 'error');
            errorCount++;
        }
        
        // Small delay between updates to avoid overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    // Update batch status message with results
    if (batchStatusMessage) {
        showStatus(batchStatusMessage, `Batch update completed: ${successCount} success, ${errorCount} errors`, 
                  errorCount === 0 ? 'success' : 'error');
    }
    
    // Re-enable form
    submitButton.disabled = false;
    dateInput.disabled = false;
    submitButton.textContent = originalButtonText;
    
    // Hide the entire group section if all photos were processed
    setTimeout(() => {
        const remainingPhotos = groupSection.querySelectorAll('.photo-pair');
        if (remainingPhotos.length === 0) {
            groupSection.style.transition = 'opacity 0.5s ease-out';
            groupSection.style.opacity = '0';
            setTimeout(() => {
                groupSection.remove();
                checkIfAllPhotosProcessed();
            }, 500);
        }
    }, 2000);
}

function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status-message ${type}`;
    element.style.display = 'block';
    
    // Auto-hide success and loading messages after some time
    if (type === 'loading') {
        // Don't auto-hide loading messages
        return;
    }
    
    if (type === 'success') {
        setTimeout(() => {
            element.style.display = 'none';
        }, 3000);
    }
}

function checkIfAllPhotosProcessed() {
    const remainingPairs = document.querySelectorAll('.photo-pair');
    
    if (remainingPairs.length === 0) {
        const main = document.querySelector('main');
        main.innerHTML = `
            <div class="no-photos">
                <h2>All photos processed!</h2>
                <p>All photos have been successfully updated with correct dates.</p>
                <p>Refresh the page to check for new photos.</p>
                <button onclick="window.location.reload()" style="margin-top: 20px; padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer;">
                    Refresh Page
                </button>
            </div>
        `;
    }
}

// Add keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Enter key submits the form if date input is focused
    if (event.key === 'Enter' && event.target.type === 'date') {
        const form = event.target.closest('.date-form');
        if (form) {
            form.querySelector('button').click();
        }
    }
    
    // Escape key clears status messages
    if (event.key === 'Escape') {
        const statusMessages = document.querySelectorAll('.status-message');
        statusMessages.forEach(msg => {
            if (!msg.classList.contains('loading')) {
                msg.style.display = 'none';
            }
        });
    }
});

// Add today's date as default for new inputs
document.addEventListener('click', function(event) {
    if (event.target.type === 'date' && !event.target.value) {
        const today = new Date().toISOString().split('T')[0];
        event.target.value = today;
    }
});

// Modal functionality
function initializeModal() {
    const modal = document.getElementById('photoModal');
    const modalImage = document.getElementById('modalImage');
    const modalLoading = document.getElementById('modalLoading');
    const closeButton = document.querySelector('.close');
    const clickablePhotos = document.querySelectorAll('.clickable-photo');
    
    // Add click handlers to all clickable photos
    clickablePhotos.forEach(photo => {
        photo.addEventListener('click', function() {
            const fullSrc = this.getAttribute('data-full-src');
            if (fullSrc) {
                // Show modal with loading state
                modal.classList.add('show');
                modalLoading.style.display = 'flex';
                modalImage.style.display = 'none';
                document.body.style.overflow = 'hidden'; // Prevent background scrolling
                
                // Create new image to preload
                const img = new Image();
                img.onload = function() {
                    // Image loaded, show it and hide loading
                    modalImage.src = fullSrc;
                    modalLoading.style.display = 'none';
                    modalImage.style.display = 'block';
                };
                img.onerror = function() {
                    // Image failed to load, show error and hide loading
                    modalLoading.innerHTML = '<div class="loading-spinner"></div><p>Failed to load full image</p>';
                    setTimeout(() => {
                        closeModal();
                    }, 2000);
                };
                img.src = fullSrc;
            }
        });
    });
    
    // Close modal when clicking the X button
    if (closeButton) {
        closeButton.addEventListener('click', closeModal);
    }
    
    // Close modal when clicking outside the image
    modal.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeModal();
        }
    });
    
    // Close modal with Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && modal.classList.contains('show')) {
            closeModal();
        }
    });
    
    function closeModal() {
        modal.classList.remove('show');
        document.body.style.overflow = ''; // Restore scrolling
        modalImage.src = ''; // Clear the image source
        modalImage.style.display = 'none';
        modalLoading.style.display = 'none';
        // Reset loading content in case of error state
        modalLoading.innerHTML = '<div class="loading-spinner"></div><p>Loading full resolution image...</p>';
    }
}

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    let searchTimeout;
    
    if (!searchInput || !searchResults) {
        console.warn('Search elements not found');
        return;
    }
    
    // Add input event listener with debouncing
    searchInput.addEventListener('input', function(event) {
        const query = event.target.value.trim();
        
        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        // Clear results if query is empty
        if (!query) {
            clearSearchResults();
            return;
        }
        
        // Debounce search - wait 300ms after user stops typing
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });
    
    // Clear search when Escape is pressed
    searchInput.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            searchInput.value = '';
            clearSearchResults();
        }
    });
}

async function performSearch(query) {
    const searchResults = document.getElementById('searchResults');
    
    try {
        // Show loading state
        searchResults.innerHTML = '<div class="search-loading">Searching...</div>';
        searchResults.style.display = 'block';
        
        const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
        const result = await response.json();
        
        if (result.success) {
            displaySearchResults(result);
        } else {
            searchResults.innerHTML = `<div class="search-error">Search failed: ${result.message}</div>`;
        }
        
    } catch (error) {
        console.error('Search error:', error);
        searchResults.innerHTML = '<div class="search-error">Search failed. Please try again.</div>';
    }
}

function displaySearchResults(result) {
    const searchResults = document.getElementById('searchResults');
    
    if (result.total_results === 0) {
        searchResults.innerHTML = `
            <div class="search-no-results">
                No photos found matching "${result.query}"
            </div>
        `;
        return;
    }
    
    let html = `
        <div class="search-header">
            Found ${result.total_results} result${result.total_results !== 1 ? 's' : ''} for "${result.query}" - Click to edit dates
        </div>
        <div class="search-results-photos">
    `;
    
    result.results.forEach(item => {
        if (item.type === 'individual') {
            html += renderSearchResultPhotoPair(item);
        }
    });
    
    html += '</div>';
    searchResults.innerHTML = html;
    
    // Re-initialize event handlers for search results
    initializeSearchResultHandlers();
}

function renderSearchResultPhotoPair(item) {
    const matchInfo = item.matched_file ? ` (matched: ${item.matched_file})` : '';
    
    return `
        <div class="photo-pair search-result-pair" data-base-name="${item.base_name}">
            <div class="photo-info">
                <h3>${item.base_name}${matchInfo}</h3>
            </div>
            
            <div class="photo-display">
                ${item.front ? `
                    <div class="photo-side">
                        <label>Front</label>
                        <img src="/thumbnails/${getFileName(item.front)}" 
                             alt="Front of ${item.base_name}" 
                             class="photo-image clickable-photo"
                             data-full-src="/photos/${getFileName(item.front)}"
                             loading="lazy"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                        <div class="image-placeholder" style="display: none;">
                            <span>Image not found</span>
                        </div>
                        <div class="filename">${getFileName(item.front)}</div>
                    </div>
                ` : ''}
                
                <div class="photo-side">
                    <label>Back</label>
                    ${item.back ? `
                        <img src="/thumbnails/${getFileName(item.back)}" 
                             alt="Back of ${item.base_name}"
                             class="photo-image clickable-photo"
                             data-full-src="/photos/${getFileName(item.back)}"
                             loading="lazy"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                        <div class="image-placeholder" style="display: none;">
                            <span>Image not found</span>
                        </div>
                        <div class="filename">${getFileName(item.back)}</div>
                    ` : `
                        <div class="image-placeholder">
                            <span>None available</span>
                        </div>
                    `}
                </div>
                
                ${item.variants.map(variant => `
                    <div class="photo-side">
                        <label>Original</label>
                        <img src="/thumbnails/${getFileName(variant)}" 
                             alt="Variant of ${item.base_name}"
                             class="photo-image clickable-photo"
                             data-full-src="/photos/${getFileName(variant)}"
                             loading="lazy"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                        <div class="image-placeholder" style="display: none;">
                            <span>Image not found</span>
                        </div>
                        <div class="filename">${getFileName(variant)}</div>
                    </div>
                `).join('')}
            </div>
            
            <div class="date-input-section">
                <form class="date-form">
                    <label for="search-date-${item.base_name}">Correct Date:</label>
                    <input type="date" 
                           id="search-date-${item.base_name}" 
                           name="date" 
                           value=""
                           required>
                    <button type="submit">Update Date</button>
                    <button type="button" class="ignore-btn">Unknown</button>
                </form>
                <div class="status-message"></div>
            </div>
        </div>
    `;
}

function initializeSearchResultHandlers() {
    // Add form submission handlers for search result photos
    const searchForms = document.querySelectorAll('.search-result-pair .date-form');
    searchForms.forEach(form => {
        form.addEventListener('submit', handleDateSubmit);
    });
    
    // Add ignore button handlers for search result photos  
    const searchIgnoreButtons = document.querySelectorAll('.search-result-pair .ignore-btn');
    searchIgnoreButtons.forEach(button => {
        button.addEventListener('click', handleIgnoreClick);
    });
    
    // Add modal handlers for search result photos
    const searchClickablePhotos = document.querySelectorAll('.search-result-pair .clickable-photo');
    searchClickablePhotos.forEach(photo => {
        photo.addEventListener('click', function() {
            const fullSrc = this.getAttribute('data-full-src');
            if (fullSrc) {
                const modal = document.getElementById('photoModal');
                const modalImage = document.getElementById('modalImage');
                const modalLoading = document.getElementById('modalLoading');
                
                // Show modal with loading state
                modal.classList.add('show');
                modalLoading.style.display = 'flex';
                modalImage.style.display = 'none';
                document.body.style.overflow = 'hidden';
                
                // Create new image to preload
                const img = new Image();
                img.onload = function() {
                    modalImage.src = fullSrc;
                    modalLoading.style.display = 'none';
                    modalImage.style.display = 'block';
                };
                img.onerror = function() {
                    modalLoading.innerHTML = '<div class="loading-spinner"></div><p>Failed to load full image</p>';
                    setTimeout(() => {
                        modal.classList.remove('show');
                        document.body.style.overflow = '';
                        modalLoading.innerHTML = '<div class="loading-spinner"></div><p>Loading full resolution image...</p>';
                    }, 2000);
                };
                img.src = fullSrc;
            }
        });
    });
    
    // Add today's date as default for search result date inputs
    const searchDateInputs = document.querySelectorAll('.search-result-pair input[type="date"]');
    searchDateInputs.forEach(input => {
        input.addEventListener('click', function() {
            if (!this.value) {
                const today = new Date().toISOString().split('T')[0];
                this.value = today;
            }
        });
    });
}

function clearSearchResults() {
    const searchResults = document.getElementById('searchResults');
    searchResults.style.display = 'none';
    searchResults.innerHTML = '';
}

function getFileName(filepath) {
    if (!filepath) return '';
    return filepath.split('/').pop().split('\\').pop();
}