document.addEventListener('DOMContentLoaded', function () {
    // Get all "Choose Image" buttons
    const chooseImageButtons = document.querySelectorAll('.choose-image-btn');

    chooseImageButtons.forEach(button => {
        button.addEventListener('click', function () {
            const choice = this.getAttribute('data-choice'); // Get the associated choice (e.g., "choice1")
            const radioQuestionImages = document.querySelector(`#id_${choice}_sign`);
            const radioQuestionInputs = radioQuestionImages ? radioQuestionImages.querySelectorAll('input') : null;

            if (radioQuestionImages) {
                // Toggle the 'hidden' class on the parent <div>
                radioQuestionImages.classList.toggle('hidden');
                radioQuestionImages.classList.toggle('custom-flex');
                console.log('Toggled hidden class on wrapper:', radioQuestionImages.classList);
            }

            if (radioQuestionInputs && radioQuestionInputs.length > 0) {
                // Loop through all <input> elements and toggle the 'hidden' class
                radioQuestionInputs.forEach(input => {
                    input.classList.toggle('hidden');
                    console.log('Toggled hidden class on input:', input.classList);
                });
            }

            const radioGroupWrapper = document.querySelector(`#id_${choice}_signs`);
            const radioInputs = radioGroupWrapper ? radioGroupWrapper.querySelectorAll('input.choice-sign-radio') : null;

            if (radioGroupWrapper) {
                // Toggle the 'hidden' class on the parent <div>
                radioGroupWrapper.classList.toggle('hidden');
                radioGroupWrapper.classList.toggle('custom-flex');
                console.log('Toggled hidden class on wrapper:', radioGroupWrapper.classList);
            } else {
                console.error(`Radio group wrapper for choice "${choice}" not found.`);
            }

            if (radioInputs && radioInputs.length > 0) {
                // Loop through all <input> elements and toggle the 'hidden' class
                radioInputs.forEach(input => {
                  input.classList.toggle('hidden');
                    
                  console.log('Toggled hidden class on input:', input.classList);
                });
            } else {
                console.error(`No radio inputs found for choice "${choice}".`);
            }
        });
    });
});