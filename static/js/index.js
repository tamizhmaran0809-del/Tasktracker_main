document.addEventListener("DOMContentLoaded", function () {

    /* ============================================================
       Sidebar active-link auto highlight
    ============================================================ */

    var currentPath = window.location.pathname.replace(/\/$/, "") || "/";
    var menuItems = document.querySelectorAll(".sidebar .menu-item");

    menuItems.forEach(function (item) {
        var href = item.getAttribute("href");

        if (!href || href === "#") {
            item.classList.remove("active");
            return;
        }

        var linkPath = href.replace(/\/$/, "") || "/";

        if (linkPath === currentPath) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    /* ============================================================
       Mobile hamburger menu toggle
    ============================================================ */

    var sidebar = document.getElementById("sidebar");
    var toggleBtn = document.getElementById("sidebarToggle");
    var backdrop = document.getElementById("sidebarBackdrop");

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener("click", function () {
            var isOpen = sidebar.classList.toggle("menu-open");
            toggleBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
            if (backdrop) backdrop.classList.toggle("visible", isOpen);
        });

        if (backdrop) {
            backdrop.addEventListener("click", function () {
                sidebar.classList.remove("menu-open");
                backdrop.classList.remove("visible");
                toggleBtn.setAttribute("aria-expanded", "false");
            });
        }

        menuItems.forEach(function (item) {
            item.addEventListener("click", function () {
                sidebar.classList.remove("menu-open");
                if (backdrop) backdrop.classList.remove("visible");
                toggleBtn.setAttribute("aria-expanded", "false");
            });
        });

        /* Close the menu on outside click */
        document.addEventListener("click", function (event) {
            var clickedInsideSidebar = sidebar.contains(event.target);
            var clickedToggle = toggleBtn.contains(event.target);

            if (!clickedInsideSidebar && !clickedToggle && sidebar.classList.contains("menu-open")) {
                sidebar.classList.remove("menu-open");
                if (backdrop) backdrop.classList.remove("visible");
                toggleBtn.setAttribute("aria-expanded", "false");
            }
        });

        /* Reset state if the viewport is resized back to desktop */
        window.addEventListener("resize", function () {
            if (window.innerWidth > 720) {
                sidebar.classList.remove("menu-open");
                if (backdrop) backdrop.classList.remove("visible");
                toggleBtn.setAttribute("aria-expanded", "false");
            }
        });
    }

});