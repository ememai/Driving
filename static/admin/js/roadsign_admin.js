document.addEventListener('DOMContentLoaded', function() {
    function toggleImageFields() {
        var choice = document.querySelector('input[name="image_choice"]:checked').value;
        var uploadField = document.querySelector('.field-sign_image');
        var existingField = document.querySelector('.field-existing_image');
        
        if (choice === 'existing') {
            if (uploadField) {
                uploadField.style.display = 'none';
                // Clear any validation errors
                var errorElement = uploadField.querySelector('.errorlist');
                if (errorElement) errorElement.remove();
            }
            if (existingField) existingField.style.display = 'block';
        } else {
            if (uploadField) uploadField.style.display = 'block';
            if (existingField) existingField.style.display = 'none';
        }
    }
    
    // Initial toggle
    toggleImageFields();
    
    // Add event listeners
    var radios = document.querySelectorAll('input[name="image_choice"]');
    radios.forEach(function(radio) {
        radio.addEventListener('change', toggleImageFields);
    });
});