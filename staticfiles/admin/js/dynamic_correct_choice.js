document.addEventListener("DOMContentLoaded", function () {
    function updateCorrectChoiceOptions() {
        const choicesField = document.querySelector("#id_choices");
        const correctChoiceField = document.querySelector("#id_correct_choice");

        if (!choicesField || !correctChoiceField) return;

        // Get selected values from choicesField
        const selectedValues = choicesField.tagName === "SELECT"
            ? Array.from(choicesField.selectedOptions).map(opt => opt.value)
            : Array.from(document.querySelectorAll("#id_choices input:checked")).map(input => input.value);

        // Clear existing radio buttons in correctChoiceField
        correctChoiceField.innerHTML = "";

        // Populate correctChoiceField with selected values as radio buttons
        selectedValues.forEach(value => {
            const label = document.createElement("label");
            const radio = document.createElement("input");
            radio.type = "radio";
            radio.name = "correct_choice";
            radio.value = value;

            // Fetch display text for the value
            let displayText = "";
            if (choicesField.tagName === "SELECT") {
                const option = Array.from(choicesField.options).find(opt => opt.value === value);
                displayText = option ? option.innerText.trim() : value;
            } else {
                const inputElement = document.querySelector(`#id_choices input[value="${CSS.escape(value)}"]`);
                const labelElement = inputElement
                    ? inputElement.closest("label")
                    : document.querySelector(`label[for="id_choices_${CSS.escape(value)}"]`);
                displayText = labelElement ? labelElement.textContent.trim() : value;
            }

            // Append radio button and display text to the label
            label.appendChild(radio);
            label.appendChild(document.createTextNode(` ${displayText}`));
            correctChoiceField.appendChild(label);
        });
    }

    // Attach event listeners for checkboxes or select changes
    const choicesInputs = document.querySelectorAll("#id_choices input");
    if (choicesInputs.length) {
        choicesInputs.forEach(input => {
            input.addEventListener("change", updateCorrectChoiceOptions);
        });
    } else if (typeof django !== "undefined" && django.jQuery) {
        django.jQuery("#id_choices").on("change", updateCorrectChoiceOptions);
    }

    // Support dynamically added formsets (e.g., filter_horizontal)
    if (typeof django !== "undefined" && django.jQuery) {
        django.jQuery(document).on("formset:added", updateCorrectChoiceOptions);
    }

    // Run once on page load
    updateCorrectChoiceOptions();
});

