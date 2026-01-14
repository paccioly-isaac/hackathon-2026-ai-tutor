export const ChatHeader = () => {
  return (
    <header className="h-16 bg-surface-light dark:bg-surface-dark border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-6 flex-shrink-0">
      <h1 className="text-xl font-semibold text-gray-800 dark:text-white">Chat</h1>
      <div className="flex items-center gap-4">
        <button className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
          <span className="material-icons">search</span>
        </button>
        <button className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
          <span className="material-icons">more_vert</span>
        </button>
      </div>
    </header>
  );
};
