import "./Footer.css";

const APP_NAME = "Avatar Server";
const VERSION = __APP_VERSION__;

export function Footer() {
  return (
    <footer className="footer">
      {APP_NAME} v{VERSION}
    </footer>
  );
}
