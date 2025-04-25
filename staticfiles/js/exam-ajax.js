document.addEventListener("DOMContentLoaded", function () {
  const container = document.getElementById("exam-container");
  const examId = container.dataset.examId;
  let currentNumber = parseInt(container.dataset.currentNumber);

  function loadQuestion(num) {
    fetch(`/exam/${examId}/ajax/${num}/`)
      .then(response => response.json())
      .then(data => {
        container.innerHTML = data.html;
        container.dataset.currentNumber = num;
        attachEvents(); // rebind buttons
      });
  }

  function attachEvents() {
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");
    const form = document.getElementById("examForm");

    if (prevBtn) {
      prevBtn.addEventListener("click", () => {
        if (currentNumber > 1) {
          saveAnswer(() => loadQuestion(currentNumber - 1));
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", () => {
        saveAnswer(() => loadQuestion(currentNumber + 1));
      });
    }

    if (form) {
      form.addEventListener("submit", function (e) {
        const submitBtn = document.getElementById("submitExamBtn");
        if (submitBtn) {
          return true;
        }
        e.preventDefault();
      });
    }
  }

  function saveAnswer(callback) {
    const form = document.getElementById("examForm");
    const formData = new FormData(form);
    fetch(form.action, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      body: formData
    }).then(() => callback());
  }

  attachEvents();
});
