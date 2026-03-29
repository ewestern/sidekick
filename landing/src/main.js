import "./style.css";

const logo = `
  <svg class="logo" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <polygon points="24,6 40,20 24,28 8,20" fill="currentColor" opacity="0.95"/>
    <polygon points="24,20 40,28 24,42 8,28" fill="currentColor" opacity="0.35"/>
  </svg>
`;

document.querySelector("#app").innerHTML = `
  <main class="shell" role="main">
    ${logo}
    <h1 class="wordmark">sidekick<span class="tld">.news</span></h1>
    <p class="tagline">Coverage of the stories that shape your community.</p>
    <p class="status">Coming soon</p>
  </main>
`;
