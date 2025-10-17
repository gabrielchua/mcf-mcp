import { createRoot } from "react-dom/client";
import App from "./jobs";
import "./jobs.css";

const root = document.getElementById("mycareersfuture-root");
if (root) {
  createRoot(root).render(<App />);
}

export { App };
export default App;
