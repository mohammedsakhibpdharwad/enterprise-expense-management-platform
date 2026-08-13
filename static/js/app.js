document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");

    if (toggle && sidebar) {
        toggle.addEventListener("click", function () {
            sidebar.classList.toggle("show");
        });

        document.addEventListener("click", function (event) {
            if (window.innerWidth >= 992) {
                return;
            }
            const isClickInside = sidebar.contains(event.target) || toggle.contains(event.target);
            if (!isClickInside && sidebar.classList.contains("show")) {
                sidebar.classList.remove("show");
            }
        });
    }
});
