// static/js/force-adv-desc.js

function adjustAdvancementDescriptions() {
    // Get all advancement elements
    const advancements = document.querySelectorAll('.advancement');
    
    advancements.forEach(advancement => {
        const advName = advancement.querySelector('.adv-name');
        const advDesc = advancement.querySelector('.adv-desc');
        
        if (advName && advDesc) {
            // Force a reflow to ensure accurate measurements
            advName.offsetHeight; // This forces the browser to calculate layout
            
            // Get the width of the name element
            const nameWidth = advName.offsetWidth + 120; // Add some extra space for padding/margin adjustments
            
            // Set the description width to match the name width
            advDesc.style.maxWidth = nameWidth + 'px';
            advDesc.style.width = nameWidth + 'px';
            
            // Enable text wrapping and height adjustment
            advDesc.style.whiteSpace = 'normal';
            advDesc.style.wordWrap = 'break-word';
            advDesc.style.overflowWrap = 'break-word';
            advDesc.style.height = 'auto';
            
            // Optional: Add some padding/margin adjustments if needed
            advDesc.style.boxSizing = 'border-box';
        }
    });
}

// Run with multiple timing strategies
document.addEventListener('DOMContentLoaded', () => {
    // Immediate execution
    adjustAdvancementDescriptions();
    
    // Small delay to ensure CSS is fully applied
    setTimeout(adjustAdvancementDescriptions, 10);
    
    // Another delay for web fonts
    setTimeout(adjustAdvancementDescriptions, 100);
});

// /static/js/force-adv-desc.js