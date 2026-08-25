(function () {
    function attachPreview(input) {
        if (!input || input.dataset.livePreviewAttached === "1") return;
        input.dataset.livePreviewAttached = "1";

        var previewBox = document.createElement("div");
        previewBox.style.cssText = "margin-top:10px;display:none;";
        previewBox.innerHTML =
            '<img style="max-width:220px;max-height:160px;object-fit:cover;border-radius:8px;border:1px solid #d1d5db;padding:4px;background:#fff;">' +
            '<div style="margin-top:6px;font-size:12px;color:#6b7280;word-break:break-all;"></div>';

        // Insert after the input's closest wrapper, not just the input itself
        var anchor = input.closest(".flex, .relative, .field-box, .form-row") || input.parentElement;
        anchor.appendChild(previewBox);

        var img = previewBox.querySelector("img");
        var fileName = previewBox.querySelector("div");

        input.addEventListener("change", function () {
            var file = input.files && input.files[0];
            if (!file || !file.type.startsWith("image/")) {
                previewBox.style.display = "none";
                img.removeAttribute("src");
                fileName.textContent = "";
                return;
            }
            fileName.textContent = file.name;
            var url = URL.createObjectURL(file);
            img.src = url;
            previewBox.style.display = "block";
            img.onload = function () { URL.revokeObjectURL(url); };
        });
    }

    function scan(root) {
        (root || document).querySelectorAll('input[type="file"]').forEach(attachPreview);
    }

    // Initial scan — delayed to let Unfold finish rendering
    function boot() {
        scan(document);

        // Watch for dynamically added inlines / widgets
        new MutationObserver(function (mutations) {
            mutations.forEach(function (m) {
                m.addedNodes.forEach(function (node) {
                    if (node.nodeType === 1) scan(node);
                });
            });
        }).observe(document.body, { childList: true, subtree: true });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            setTimeout(boot, 300);
        });
    } else {
        setTimeout(boot, 300);
    }
})();