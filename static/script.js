
<script>
document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("issueSearch");
    const statusFilter = document.getElementById("statusFilter");
    const issueRows = document.querySelectorAll(".issue-row");

    function filterIssues() {
        const search = searchInput.value.toLowerCase().trim();
        const status = statusFilter.value;

        issueRows.forEach(row => {
            const text = row.innerText.toLowerCase();
            const selectedStatus =
                row.querySelector(".status-select").value;

            const matchesSearch = text.includes(search);
            const matchesStatus =
                status === "all" || selectedStatus === status;

            row.style.display =
                matchesSearch && matchesStatus ? "flex" : "none";
        });
    }

    searchInput.addEventListener("input", filterIssues);
    statusFilter.addEventListener("change", filterIssues);
});
</script>