export const Sidebar = () => {
  return (
    <aside className="w-64 bg-surface-light dark:bg-surface-dark border-r border-gray-200 dark:border-gray-700 flex flex-col flex-shrink-0 transition-colors duration-300">
      <div className="h-16 flex items-center px-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 text-primary font-bold text-xl">
          <span className="material-icons">school</span>
          <span>EduLearn</span>
        </div>
      </div>

      <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
        <a
          className="flex items-center gap-3 px-4 py-3 bg-primary/10 text-primary rounded-lg font-medium transition-colors"
          href="#"
        >
          <span className="material-icons text-xl">chat_bubble_outline</span>
          Chat
        </a>
        <a
          className="flex items-center gap-3 px-4 py-3 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg font-medium transition-colors"
          href="#"
        >
          <span className="material-icons text-xl">library_books</span>
          Materials
        </a>
        <a
          className="flex items-center gap-3 px-4 py-3 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg font-medium transition-colors"
          href="#"
        >
          <span className="material-icons text-xl">assignment</span>
          Exercises
        </a>
      </nav>

      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <img
            alt="User Avatar"
            className="w-10 h-10 rounded-full object-cover"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuBDms81vCm1mscKQTrrz3cagUl6e8-LOC6ES_IJm141SSmfor2SLt9VnSO1qY-fFiCde_9cRHUs40rugDB8qVQU0uiTJ4HfPUL91qJBeE_Xk2OrHCdSPAFHngd6miIy1mcbRs0ZAUcPCNJRoxrCa6CIKTJBpYtLLqiDq4WZ1zV-D_3U2PHq2LoHOx_tfJ9CfbX9l9V5K22psqdggNjYtwK0R_5ZN5zwNlMiTengZ5h8PrTjioM8NCcq0hsief0cFb8Oaec1mM5khw"
          />
          <div>
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">Alex Student</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Pro Plan</p>
          </div>
        </div>
      </div>
    </aside>
  );
};
