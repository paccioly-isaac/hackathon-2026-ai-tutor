export const TypingIndicator = () => {
  return (
    <div className="flex gap-4">
      <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center flex-shrink-0 text-indigo-600 dark:text-indigo-300">
        <span className="material-icons text-xl">smart_toy</span>
      </div>
      <div className="bg-surface-light dark:bg-surface-dark p-4 rounded-2xl rounded-tl-none shadow-sm border border-gray-100 dark:border-gray-700 flex items-center gap-2">
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
        <span
          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
          style={{ animationDelay: '0.2s' }}
        ></span>
        <span
          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
          style={{ animationDelay: '0.4s' }}
        ></span>
      </div>
    </div>
  );
};
