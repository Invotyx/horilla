(function () {
  "use strict";

  const ROOT_SELECTOR = "#attendance-task-logger";
  const CHECK_OUT_PATH = "/attendance/clock-out";
  const CHECK_IN_PATH = "/attendance/clock-in";

  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function parseResponse(response) {
    return response
      .json()
      .catch(() => ({}))
      .then((data) => {
        if (!response.ok) {
          const error = new Error((data && data.error) || "Request failed");
          error.data = data;
          error.status = response.status;
          throw error;
        }
        return data;
      });
  }

  class TaskTimerDropdown {
    constructor(root) {
      this.root = root;
      this.dropdown = root.querySelector('[data-role="task-dropdown"]');
      this.toggleButton = root.querySelector('[data-role="task-toggle"]');
      this.menu = root.querySelector('[data-role="task-menu"]');
      this.label = root.querySelector('[data-role="task-label"]');
      this.selectedTime = root.querySelector('[data-role="task-time"]');
      this.error = root.querySelector('[data-role="task-error"]');
      this.optionsUrl = root.dataset.optionsUrl;
      this.toggleUrl = root.dataset.toggleUrl;
      this.stopUrl = root.dataset.stopUrl;
      this.buttonContainer = root.querySelector("#check-in-out-button");
      this.defaultLabel = this.label ? this.label.textContent.trim() : "";
      this.activeTask = null;
      this.hasTasks = false;
      this.loading = false;
      this.pendingRefresh = false;

      this.boundToggleClick = this.handleToggleClick.bind(this);
      this.boundDocumentClick = this.handleDocumentClick.bind(this);
      this.boundMenuClick = this.handleMenuClick.bind(this);

      if (this.toggleButton) {
        this.toggleButton.addEventListener("click", this.boundToggleClick);
      }
      if (this.menu) {
        this.menu.addEventListener("click", this.boundMenuClick);
      }
      document.addEventListener("click", this.boundDocumentClick);

      this.refreshState();
      this.refreshTasks();
    }

    destroy() {
      if (this.toggleButton) {
        this.toggleButton.removeEventListener("click", this.boundToggleClick);
      }
      if (this.menu) {
        this.menu.removeEventListener("click", this.boundMenuClick);
      }
      document.removeEventListener("click", this.boundDocumentClick);
      this.closeMenu();
    }

    refreshState() {
      const button = this.buttonContainer
        ? this.buttonContainer.querySelector("button")
        : null;
      if (button) {
        const hxGet = button.getAttribute("hx-get") || "";
        this.isClockedIn = hxGet.indexOf(CHECK_OUT_PATH) !== -1;
      } else {
        this.isClockedIn = false;
      }
      this.root.dataset.clockedIn = this.isClockedIn ? "1" : "0";
      this.updateToggleAvailability();
    }

    updateToggleAvailability() {
      const shouldDisable = !this.isClockedIn || !this.hasTasks;
      if (this.toggleButton) {
        this.toggleButton.disabled = shouldDisable;
      }
      this.root.classList.toggle(
        "attendance-task-dropdown--disabled",
        shouldDisable
      );
    }

    refreshTasks() {
      if (this.loading) {
        this.pendingRefresh = true;
        return;
      }
      if (!this.optionsUrl) {
        return;
      }
      this.loading = true;
      fetch(this.optionsUrl, {
        credentials: "same-origin",
      })
        .then(parseResponse)
        .then((data) => {
          this.populateMenu(data || {});
          this.setActiveLabel(data ? data.active : null);
          this.clearError();
        })
        .catch((error) => {
          if (error && error.data && error.data.error) {
            this.showError(error.data.error);
          } else {
            this.showError("Unable to load tasks. Please try again.");
          }
        })
        .finally(() => {
          this.loading = false;
          this.updateToggleAvailability();
          if (this.pendingRefresh) {
            this.pendingRefresh = false;
            this.refreshTasks();
          }
        });
    }

    populateMenu(payload) {
      if (!this.menu) {
        return;
      }
      const projects = (payload && payload.projects) || [];
      this.menu.innerHTML = "";
      this.hasTasks = false;

      if (!projects.length) {
        const empty = document.createElement("div");
        empty.className = "attendance-task-dropdown__empty text-muted px-3 py-2";
        empty.textContent = this.menu.getAttribute("data-empty-label") || "No tasks available";
        this.menu.appendChild(empty);
        this.hasTasks = false;
        return;
      }

      projects.forEach((project) => {
        if (!project || !project.tasks || !project.tasks.length) {
          return;
        }
        this.hasTasks = true;
        const header = document.createElement("div");
        header.className = "attendance-task-dropdown__group-title";
        header.textContent = project.name || "";
        this.menu.appendChild(header);

        project.tasks.forEach((task) => {
          if (!task) {
            return;
          }
          const item = document.createElement("button");
          item.type = "button";
          item.className = "attendance-task-dropdown__item";
          item.setAttribute("data-project-id", task.project_id);
          item.setAttribute("data-task-name", task.task_name);
          if (task.active) {
            item.classList.add("is-active");
          }

          const indicator = document.createElement("span");
          indicator.className = "attendance-task-dropdown__indicator";
          item.appendChild(indicator);

          const label = document.createElement("span");
          label.textContent = task.label || task.task_name;
          item.appendChild(label);

          const time = document.createElement("span");
          time.className = "attendance-task-dropdown__time";
          time.textContent = task.time_display || "00:00";
          item.appendChild(time);

          this.menu.appendChild(item);
        });
      });

      this.updateToggleAvailability();
    }

    setActiveLabel(active) {
      this.activeTask = active || null;
      if (!this.label) {
        return;
      }
      if (this.activeTask) {
        this.label.textContent = this.activeTask.label || this.defaultLabel;
        if (this.selectedTime) {
          this.selectedTime.textContent = this.activeTask.time_display
            ? this.activeTask.time_display
            : "";
        }
      } else {
        this.label.textContent = this.defaultLabel;
        if (this.selectedTime) {
          this.selectedTime.textContent = "";
        }
      }
    }

    handleToggleClick(event) {
      event.preventDefault();
      if (this.toggleButton && this.toggleButton.disabled) {
        return;
      }
      if (!this.menu) {
        return;
      }
      if (this.menu.classList.contains("show")) {
        this.closeMenu();
      } else {
        this.openMenu();
      }
    }

    handleDocumentClick(event) {
      if (!this.menu || !this.menu.classList.contains("show")) {
        return;
      }
      if (this.root.contains(event.target)) {
        return;
      }
      this.closeMenu();
    }

    handleMenuClick(event) {
      const target = event.target.closest(".attendance-task-dropdown__item");
      if (!target || (this.toggleButton && this.toggleButton.disabled)) {
        return;
      }
      event.preventDefault();
      const projectId = target.getAttribute("data-project-id");
      const taskName = target.getAttribute("data-task-name");
      if (!projectId || !taskName) {
        return;
      }
      this.toggleTask(projectId, taskName);
    }

    openMenu() {
      if (this.menu) {
        this.menu.classList.add("show");
      }
      if (this.toggleButton) {
        this.toggleButton.setAttribute("aria-expanded", "true");
      }
    }

    closeMenu() {
      if (this.menu) {
        this.menu.classList.remove("show");
      }
      if (this.toggleButton) {
        this.toggleButton.setAttribute("aria-expanded", "false");
      }
    }

    toggleTask(projectId, taskName) {
      if (!this.toggleUrl) {
        return;
      }
      this.clearError();
      fetch(this.toggleUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ project_id: projectId, task_name: taskName }),
      })
        .then(parseResponse)
        .then((data) => {
          this.closeMenu();
          if (data && data.active) {
            this.setActiveLabel(data.active);
          } else {
            this.setActiveLabel(null);
          }
          this.refreshTasks();
        })
        .catch((error) => {
          if (error && error.data && error.data.error) {
            this.showError(error.data.error);
          } else {
            this.showError("Unable to update the task timer.");
          }
        });
    }

    stopActive(markComplete) {
      if (!this.stopUrl) {
        return Promise.resolve();
      }
      const url = markComplete ? `${this.stopUrl}?complete=1` : this.stopUrl;
      return fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCsrfToken(),
        },
      })
        .then(parseResponse)
        .then((data) => {
          if (data && data.log) {
            this.setActiveLabel(null);
            this.refreshTasks();
          }
        })
        .catch(() => {
          /* Ignore stop errors silently */
        });
    }

    showError(message) {
      if (!this.error) {
        return;
      }
      this.error.textContent = message;
      this.error.classList.remove("d-none");
    }

    clearError() {
      if (!this.error) {
        return;
      }
      this.error.textContent = "";
      this.error.classList.add("d-none");
    }
  }

  const Manager = {
    instance: null,

    init() {
      const root = document.querySelector(ROOT_SELECTOR);
      if (!root) {
        if (this.instance) {
          this.instance.destroy();
          this.instance = null;
        }
        return;
      }
      if (this.instance && this.instance.root === root) {
        this.instance.refreshState();
        this.instance.refreshTasks();
        return;
      }
      if (this.instance) {
        this.instance.destroy();
      }
      this.instance = new TaskTimerDropdown(root);
    },

    handleHtmxSwap(event) {
      if (!event.detail || !event.detail.xhr) {
        this.init();
        return;
      }
      const url = event.detail.xhr.responseURL || "";
      const status = event.detail.xhr.status || 0;
      const success = status >= 200 && status < 300;
      if (!this.instance) {
        this.init();
      }
      if (!this.instance) {
        return;
      }
      if (url.indexOf(CHECK_OUT_PATH) !== -1 && success) {
        this.instance
          .stopActive(true)
          .finally(() => {
            this.instance.refreshState();
            this.instance.refreshTasks();
          });
      } else if (url.indexOf(CHECK_IN_PATH) !== -1 && success) {
        this.instance.refreshState();
        this.instance.refreshTasks();
      } else if (
        event.detail.target &&
        event.detail.target.id === "check-in-out-button"
      ) {
        this.instance.refreshState();
      } else {
        this.init();
      }
    },
  };

  function onReady() {
    Manager.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onReady);
  } else {
    onReady();
  }

  document.body.addEventListener("htmx:afterSwap", function (event) {
    const targetId = event.detail && event.detail.target && event.detail.target.id;
    if (targetId === "check-in-out-button" || targetId === "attendance-activity-container") {
      Manager.handleHtmxSwap(event);
    }
  });
})();
