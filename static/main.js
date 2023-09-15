
    window.addEventListener('scroll', function() {
      var icon = document.querySelector('.fixed-icon');
      var scrollPosition = window.scrollY || window.pageYOffset;

      if (scrollPosition === 0) {
        icon.classList.add('hidden');
      } else {
        icon.classList.remove('hidden');
      }
    });

