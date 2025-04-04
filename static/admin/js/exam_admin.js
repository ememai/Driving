// static/admin/js/exam_admin.js
django.jQuery(document).ready(function($) {
  // Watch for exam type changes
  $('#id_exam_type').change(function() {
      var examTypeId = $(this).val();
      var questionsSelect = $('#id_questions');
      
      if (examTypeId) {
          // Show loading indicator
          questionsSelect.prev('.selector').find('.selector-available').html('<p>Loading questions...</p>');
          
          // Get CSRF token
          function getCookie(name) {
              var cookieValue = null;
              if (document.cookie && document.cookie !== '') {
                  var cookies = document.cookie.split(';');
                  for (var i = 0; i < cookies.length; i++) {
                      var cookie = $.trim(cookies[i]);
                      if (cookie.substring(0, name.length + 1) === (name + '=')) {
                          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                          break;
                      }
                  }
              }
              return cookieValue;
          }
          var csrftoken = getCookie('csrftoken');
          
          // Make AJAX request
          $.ajax({
              url: window.location.pathname,
              type: 'GET',
              data: {
                  'exam_type': examTypeId
              },
              beforeSend: function(xhr) {
                  xhr.setRequestHeader('X-CSRFToken', csrftoken);
              },
              success: function(data) {
                  // The admin's filter_horizontal widget will handle the refresh
                  // Trigger a form change to force widget update
                  questionsSelect.trigger('change');
              },
              error: function() {
                  alert('Error loading questions');
              }
          });
      } else {
          // Clear questions if no exam type selected
          questionsSelect.empty();
          questionsSelect.trigger('change');
      }
  });
  
  // Trigger change on initial load if exam type is selected
  if ($('#id_exam_type').val()) {
      $('#id_exam_type').trigger('change');
  }
});