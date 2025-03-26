document.addEventListener("DOMContentLoaded", function() {
    // Highlight correct choice in form
    function highlightCorrectChoice() {
        const correctChoice = document.querySelector("[name=correct_choice]:checked").value;
        
        // Reset all highlights
        document.querySelectorAll(".choice-group").forEach(group => {
            group.style.border = "1px solid #ddd";
        });
        
        // Highlight correct choice
        const correctGroup = document.querySelector(`.choice-group[data-choice-num="${correctChoice}"]`);
        if (correctGroup) {
            correctGroup.style.border = "2px solid green";
        }
    }
    
    // Initialize and add event listeners
    if (document.querySelector("[name=correct_choice]")) {
        highlightCorrectChoice();
        document.querySelectorAll("[name=correct_choice]").forEach(radio => {
            radio.addEventListener("change", highlightCorrectChoice);
        });
    }
    
    // Toggle visibility of text/sign fields based on content
    function toggleChoiceFields() {
        for (let i = 1; i <= 4; i++) {
            const textField = document.getElementById(`id_choice${i}_text`);
            const signsField = document.getElementById(`id_choice${i}_signs`);
            
            if (textField && signsField) {
                const textGroup = textField.closest(".fieldBox");
                const signsGroup = signsField.closest(".fieldBox");
                
                if (textField.value) {
                    signsGroup.style.display = 'none';
                } else {
                    signsGroup.style.display = 'block';
                }
                
                // Add change listeners
                textField.addEventListener('input', function() {
                    signsGroup.style.display = this.value ? 'none' : 'block';
                });
            }
        }
    }
    toggleChoiceFields();
});