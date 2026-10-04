(() => {
  const buttons = [...document.querySelectorAll(".filter-button")];
  const releases = [...document.querySelectorAll(".release")];
  const repositories = [...document.querySelectorAll(".repo-block")];

  function matches(release, filter) {
    if (filter === "all") return true;
    const isPrerelease = release.dataset.prerelease === "true";
    return filter === "prerelease" ? isPrerelease : !isPrerelease;
  }

  function applyFilter(filter) {
    for (const release of releases) {
      release.hidden = !matches(release, filter);
    }

    for (const repository of repositories) {
      repository.hidden = ![...repository.querySelectorAll(".release")].some(
        (release) => !release.hidden,
      );
    }

    for (const button of buttons) {
      const active = button.dataset.filter === filter;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    }
  }

  for (const button of buttons) {
    button.addEventListener("click", () => applyFilter(button.dataset.filter));
  }
})();
