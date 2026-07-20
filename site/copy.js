// Copy affordance for code blocks wrapped in .code-copy. The command text has
// one owner: the <code> element. The button reads it, never a duplicated string.
for (const wrap of document.querySelectorAll(".code-copy")) {
  const btn = wrap.querySelector(".copy-btn");
  const code = wrap.querySelector("code");
  if (!btn || !code) continue;
  let reset;
  btn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(code.textContent.trim());
      wrap.classList.add("copied");
      clearTimeout(reset);
      reset = setTimeout(() => wrap.classList.remove("copied"), 1600);
    } catch {
      // clipboard unavailable (insecure context or denied); leave the block as-is
    }
  });
}
