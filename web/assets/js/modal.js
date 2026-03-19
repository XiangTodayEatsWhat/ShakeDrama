/**
 * 自定义模态框组件
 * 统一风格的弹窗，替代原生 alert/confirm
 */

// 显示提示框
function showAlert(message, type = 'info') {
  const icons = {
    success: 'bi-check-circle-fill',
    error: 'bi-x-circle-fill',
    warning: 'bi-exclamation-triangle-fill',
    info: 'bi-info-circle-fill'
  };
  
  const colors = {
    success: '#28a745',
    error: '#dc3545',
    warning: '#ffc107',
    info: '#17a2b8'
  };

  const modal = document.createElement('div');
  modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10010; animation: fadeIn 0.3s;';
  
  modal.innerHTML = `
    <div style="background: white; padding: 40px 50px; border-radius: 12px; max-width: 580px; width: 92%; box-shadow: 0 20px 60px rgba(0,0,0,0.3); animation: slideDown 0.3s;">
      <div style="text-align: center; margin-bottom: 24px;">
        <i class="bi ${icons[type]}" style="font-size: 64px; color: ${colors[type]};"></i>
      </div>
      <div style="text-align: center; font-size: 16px; color: #313131; line-height: 1.6; margin-bottom: 32px;">
        ${message}
      </div>
      <div style="text-align: center;">
        <button onclick="this.closest('[style*=fixed]').remove()" class="btn-primary" style="display: inline-flex; align-items: center; gap: 8px; padding: 14px 40px; background: var(--accent-color); color: var(--contrast-color); border: none; border-radius: 6px; font-weight: 500; cursor: pointer; font-size: 16px;">
          <span>确定</span>
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // 点击背景关闭
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });

  // ESC键关闭
  const handleEsc = (e) => {
    if (e.key === 'Escape') {
      modal.remove();
      document.removeEventListener('keydown', handleEsc);
    }
  };
  document.addEventListener('keydown', handleEsc);

  return new Promise((resolve) => {
    modal.querySelector('button').addEventListener('click', () => {
      resolve(true);
    });
  });
}

// 显示确认框
function showConfirm(message, title = '确认操作') {
  return new Promise((resolve) => {
    const modal = document.createElement('div');
    modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10010; animation: fadeIn 0.3s;';
    
    modal.innerHTML = `
      <div style="background: white; padding: 40px 50px; border-radius: 12px; max-width: 580px; width: 92%; box-shadow: 0 20px 60px rgba(0,0,0,0.3); animation: slideDown 0.3s;">
        <div style="margin-bottom: 24px;">
          <h3 style="margin: 0; font-size: 24px; color: #313131; font-weight: 600;">${title}</h3>
        </div>
        <div style="font-size: 16px; color: #666; line-height: 1.6; margin-bottom: 32px;">
          ${message}
        </div>
        <div style="display: flex; gap: 12px; justify-content: flex-end;">
          <button class="btn-cancel" style="padding: 12px 32px; background: transparent; color: #666; border: 2px solid rgba(102,102,102,0.2); border-radius: 6px; font-weight: 500; cursor: pointer; font-size: 15px; transition: all 0.3s;">
            取消
          </button>
          <button class="btn-confirm" style="padding: 12px 32px; background: var(--accent-color); color: white; border: none; border-radius: 6px; font-weight: 500; cursor: pointer; font-size: 15px; transition: all 0.3s;">
            确定
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const handleResult = (result) => {
      document.removeEventListener('keydown', handleEsc);
      resolve(result);
      setTimeout(() => modal.remove(), 150);
    };

    // 按钮事件
    modal.querySelector('.btn-cancel').addEventListener('click', () => handleResult(false));
    modal.querySelector('.btn-confirm').addEventListener('click', () => handleResult(true));

    // 点击背景取消
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        handleResult(false);
      }
    });

    // ESC键取消
    const handleEsc = (e) => {
      if (e.key === 'Escape') {
        handleResult(false);
      }
    };
    document.addEventListener('keydown', handleEsc);
  });
}

// 显示加载中
function showLoading(message = '加载中...') {
  const modal = document.createElement('div');
  modal.id = 'loadingModal';
  modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10010;';
  
  modal.innerHTML = `
    <div style="background: white; padding: 40px 50px; border-radius: 12px; text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
      <div class="spinner-border text-primary" role="status" style="width: 48px; height: 48px; margin-bottom: 20px;">
        <span class="visually-hidden">加载中...</span>
      </div>
      <div style="font-size: 16px; color: #313131;">${message}</div>
    </div>
  `;

  document.body.appendChild(modal);
  return modal;
}

// 关闭加载中
function hideLoading() {
  const modal = document.getElementById('loadingModal');
  if (modal) {
    modal.remove();
  }
}

// 添加动画CSS
const style = document.createElement('style');
style.textContent = `
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  
  @keyframes slideDown {
    from { 
      opacity: 0;
      transform: translateY(-50px);
    }
    to { 
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  .btn-cancel:hover {
    background: rgba(102,102,102,0.05) !important;
    border-color: rgba(102,102,102,0.3) !important;
  }
  
  .btn-confirm:hover,
  .btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }
  
  .btn-confirm:active,
  .btn-primary:active {
    transform: translateY(0);
  }
`;
document.head.appendChild(style);
