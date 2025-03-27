document.addEventListener('DOMContentLoaded', function () {
    // Get all "Choose Image" buttons
    const chooseImageButtons = document.querySelectorAll('.choose-image-btn');

    chooseImageButtons.forEach(button => {
        button.addEventListener('click', function () {
            const choice = this.getAttribute('data-choice'); // Get the associated choice (e.g., "choice1")
            const radioGroupWrapper = document.querySelector(`#id_${choice}_signs`); // Target the parent <div>
            const radioInputs = radioGroupWrapper.querySelectorAll('input.choice-sign-radio'); // Target all <input> elements inside the parent <div>

            console.log('Button clicked:', this);
            console.log('Associated choice:', choice);
            console.log('Radio group wrapper:', radioGroupWrapper);
            console.log('Radio inputs:', radioInputs);

            if (radioGroupWrapper) {
                // Toggle the 'hidden' class on the parent <div>
                radioGroupWrapper.classList.toggle('hidden');
                console.log('Toggled hidden class on wrapper:', radioGroupWrapper.classList);
            } else {
                console.error(`Radio group wrapper for choice "${choice}" not found.`);
            }

            if (radioInputs.length > 0) {
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