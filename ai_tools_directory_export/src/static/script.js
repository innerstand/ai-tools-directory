document.addEventListener("DOMContentLoaded", function() {
    const emailForm = document.getElementById("email-form");
    const emailCaptureSection = document.getElementById("email-capture-section");
    const directorySection = document.getElementById("directory-section");
    const messageDiv = document.getElementById("message");
    const toolsContainer = document.getElementById("tools-grid");
    const departmentFilter = document.getElementById("department-filter");
    const skillFilter = document.getElementById("skill-level-filter");
    const searchInput = document.getElementById("search-bar");

    if (emailForm) {
        emailForm.addEventListener("submit", function(event) {
            event.preventDefault(); // Prevent default form submission

            const name = document.getElementById("name").value;
            const email = document.getElementById("email").value;
            const company = document.getElementById("company").value;

            if (!name || !email) {
                messageDiv.textContent = "Name and Email are required.";
                messageDiv.style.color = "red";
                return;
            }

            fetch("/api/submit-email", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ name: name, email: email, company: company }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Hide the entire email capture section instead of just the form
                    if (emailCaptureSection) {
                        emailCaptureSection.style.display = "none";
                    }
                    
                    // Remove the hidden class from directory section
                    if (directorySection) {
                        directorySection.classList.remove("hidden");
                    }
                    
                    loadTools(); // Load tools after successful submission
                } else {
                    messageDiv.textContent = "Submission failed: " + data.message;
                    messageDiv.style.color = "red";
                }
            })
            .catch(error => {
                console.error("Error:", error);
                messageDiv.textContent = "An error occurred. Please try again.";
                messageDiv.style.color = "red";
            });
        });
    }

    function loadTools() {
        fetch("/tools.json")
            .then(response => response.json())
            .then(data => {
                if (!toolsContainer) return;

                toolsContainer.innerHTML = ""; // Clear existing tools

                // Create department and skill level filters (if not already created)
                createFilters(data);

                renderTools(data); // Initial render

                // Add event listeners for filters
                if (departmentFilter) departmentFilter.addEventListener("change", () => filterAndRenderTools(data));
                if (skillFilter) skillFilter.addEventListener("change", () => filterAndRenderTools(data));
                if (searchInput) searchInput.addEventListener("input", () => filterAndRenderTools(data));
            })
            .catch(error => console.error("Error loading tools:", error));
    }

    function createFilters(tools) {
        if (!departmentFilter) return;

        // Populate department filters
        // Clear existing options first (except the "All Departments" default)
        while (departmentFilter.options.length > 1) {
            departmentFilter.remove(1);
        }
        const departments = [...new Set(tools.map(tool => tool.department))];
        departments.forEach(dept => {
            if (dept) { // Ensure dept is not null or undefined
                const option = document.createElement("option");
                option.value = dept;
                option.textContent = dept;
                departmentFilter.appendChild(option);
            }
        });

        // Skill levels are already defined in HTML
    }

    function filterAndRenderTools(allTools) {
        const selectedDepartment = departmentFilter ? departmentFilter.value : "all";
        const selectedSkill = skillFilter ? skillFilter.value : "all";
        const searchTerm = searchInput ? searchInput.value.toLowerCase() : "";

        const filteredTools = allTools.filter(tool => {
            const matchesDepartment = selectedDepartment === "all" || tool.department === selectedDepartment;
            const matchesSkill = selectedSkill === "all" || tool.skill_level === selectedSkill;
            const nameMatch = tool.name && tool.name.toLowerCase().includes(searchTerm);
            const descriptionMatch = tool.description && tool.description.toLowerCase().includes(searchTerm);
            const categoryMatch = tool.category && tool.category.toLowerCase().includes(searchTerm);
            const matchesSearch = nameMatch || descriptionMatch || categoryMatch;
            return matchesDepartment && matchesSkill && matchesSearch;
        });
        renderTools(filteredTools);
    }

    function renderTools(tools) {
        if (!toolsContainer) return;
        toolsContainer.innerHTML = ""; // Clear existing tools

        if (tools.length === 0) {
            toolsContainer.innerHTML = "<p>No tools match your criteria.</p>";
            return;
        }

        tools.forEach(tool => {
            const toolDiv = document.createElement("div");
            toolDiv.className = "tool-card";
            toolDiv.innerHTML = `
                <h3>${tool.name}</h3>
                <p><strong>Category:</strong> ${tool.category || 'N/A'}</p>
                <p><strong>Department:</strong> ${tool.department}</p>
                <p><strong>Skill Level:</strong> ${tool.skill_level}</p>
                <p><strong>Description:</strong> ${tool.description}</p>
                <p><strong>Pricing:</strong> ${tool.pricing || 'N/A'}</p>
                <p><a href="${tool.website_url}" target="_blank" class="website-link">Visit Website</a></p>
            `;
            toolsContainer.appendChild(toolDiv);
        });
    }
});
