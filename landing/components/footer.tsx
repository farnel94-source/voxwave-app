export default function Footer() {
  return (
    <footer className="border-t border-border/50 px-6 py-8">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 text-sm text-text-tertiary sm:flex-row">
        <span className="font-medium text-text-secondary">VoxWave</span>
        <div className="flex gap-6">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-text-primary"
          >
            GitHub
          </a>
          <a href="#" className="transition-colors hover:text-text-primary">
            Contact
          </a>
          <a href="#" className="transition-colors hover:text-text-primary">
            Mentions légales
          </a>
        </div>
        <span>Made with 🎙️</span>
      </div>
    </footer>
  );
}
