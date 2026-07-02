// main.js — students will add JavaScript here as features are built

// ------------------------------------------------------------------ //
// Video modal (landing page)                                          //
// ------------------------------------------------------------------ //

(function () {
    const VIDEO_ID = "dQw4w9WgXcQ"; // placeholder — replace with real YouTube ID
    const EMBED_SRC = "https://www.youtube.com/embed/" + VIDEO_ID + "?autoplay=1&rel=0";

    const trigger = document.getElementById("see-how-btn");
    const modal = document.getElementById("video-modal");
    const iframe = document.getElementById("video-modal-iframe");
    if (!trigger || !modal || !iframe) return;

    function openModal() {
        // Only set the src on first open so autoplay kicks in; subsequent
        // opens also re-set it (cheap) so the video always restarts cleanly.
        iframe.src = EMBED_SRC;
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        // Clear src — this is what actually stops the video. Setting src
        // to "" tears down the iframe's media pipeline, so audio/video
        // does not keep playing in the background.
        iframe.src = "";
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
    }

    trigger.addEventListener("click", function (e) {
        e.preventDefault();
        openModal();
    });

    // Any element with [data-modal-close] (backdrop + the × button) closes it.
    modal.addEventListener("click", function (e) {
        if (e.target.closest("[data-modal-close]")) {
            closeModal();
        }
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && modal.classList.contains("is-open")) {
            closeModal();
        }
    });
})();
