// AssetFlow Single Page Application Logic
const API_BASE = 'http://localhost:8000';

// Global Application State
const state = {
  user: null,
  token: null,
  currentView: 'dashboard',
  departments: [],
  categories: [],
  employees: [],
  allAssets: [],
  charts: {
    utilization: null,
    maintenance: null
  }
};

// ==================== UTILITY: TOAST NOTIFICATIONS ====================
function showToast(title, message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  // Set icon depending on type
  let iconName = 'info';
  if (type === 'success') iconName = 'check-circle';
  if (type === 'error') iconName = 'alert-octagon';
  if (type === 'warning') iconName = 'alert-triangle';

  toast.innerHTML = `
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    </div>
  `;

  container.appendChild(toast);
  
  // Trigger animations
  setTimeout(() => {
    toast.classList.add('fade-out');
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 4000);
}

// ==================== UTILITY: API FETCH WRAPPER ====================
async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  
  // Setup headers
  options.headers = options.headers || {};
  if (!(options.body instanceof FormData)) {
    options.headers['Content-Type'] = options.headers['Content-Type'] || 'application/json';
  }
  
  // Inject Bearer JWT Token
  const token = state.token || localStorage.getItem('token');
  if (token) {
    options.headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, options);
    
    // Handle Unauthorized (401)
    if (response.status === 401) {
      showToast('Session Expired', 'Please log in again.', 'warning');
      logout();
      return null;
    }

    // Parse JSON
    let data = null;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      // Could be binary (CSV export) or simple text
      return response;
    }

    if (!response.ok) {
      const errMsg = data?.detail || 'An error occurred during the request.';
      showToast('Error', errMsg, 'error');
      // Pass conflict states (409) to caller for specific inline handling
      if (response.status === 409) {
        return { error: true, status: 409, detail: errMsg };
      }
      return null;
    }

    return data;
  } catch (err) {
    console.error('Fetch error:', err);
    showToast('Network Error', 'Cannot connect to the backend server.', 'error');
    return null;
  }
}

// ==================== AUTHENTICATION ACTIONS ====================
async function login(email, password) {
  const result = await apiFetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  });

  if (result && result.access_token) {
    state.token = result.access_token;
    localStorage.setItem('token', result.access_token);
    showToast('Success', 'Logged in successfully!', 'success');
    
    const userProfile = await apiFetch('/api/auth/me');
    if (userProfile) {
      state.user = userProfile;
      setupUserEnvironment();
      switchView('dashboard');
    }
  }
}

async function signup(name, email, password) {
  const result = await apiFetch('/api/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ name, email, password, role: 'employee', status: 'Active' })
  });

  if (result) {
    showToast('Account Created', 'Default employee account registered. Logging in...', 'success');
    await login(email, password);
  }
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem('token');
  
  // Toggle views
  document.getElementById('auth-container').classList.remove('d-none');
  document.getElementById('app-wrapper').classList.add('d-none');
  
  // Clear forms
  document.getElementById('login-form').reset();
  document.getElementById('signup-form').reset();
}

async function validateSession() {
  const storedToken = localStorage.getItem('token');
  if (storedToken) {
    state.token = storedToken;
    const userProfile = await apiFetch('/api/auth/me');
    if (userProfile) {
      state.user = userProfile;
      setupUserEnvironment();
      switchView('dashboard');
      return;
    }
  }
  logout();
}

function setupUserEnvironment() {
  // Update header and profile indicators
  document.getElementById('header-user-display').textContent = state.user.name;
  document.getElementById('sidebar-user-name').textContent = state.user.name;
  
  // Set short avatar name (initials)
  const initials = state.user.name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
  document.getElementById('user-avatar').textContent = initials;
  document.getElementById('sidebar-user-role').textContent = state.user.role.replace('_', ' ');

  // Show/Hide Role Restricted Sidebar Nav items
  const isManagerOrAdmin = ['admin', 'asset_manager'].includes(state.user.role);
  const isAdmin = state.user.role === 'admin';

  document.getElementById('nav-reports').style.display = (isManagerOrAdmin || state.user.role === 'department_head') ? 'block' : 'none';
  document.getElementById('nav-admin').style.display = isAdmin ? 'block' : 'none';
  document.getElementById('nav-logs').style.display = isManagerOrAdmin ? 'block' : 'none';
  
  // Show registration buttons to asset managers
  document.getElementById('btn-open-register-modal').style.display = isManagerOrAdmin ? 'inline-flex' : 'none';
  document.getElementById('qa-register').style.display = isManagerOrAdmin ? 'flex' : 'none';

  // Toggle allocation form container
  document.getElementById('allocation-form-card').style.display = isManagerOrAdmin ? 'block' : 'none';

  // Load all background directory variables
  loadSupportingData();
  
  // Start Notification Polling/Count load
  updateNotificationBadge();
}

// Load static lists for selectors and admin panels
async function loadSupportingData() {
  const depts = await apiFetch('/api/org/departments');
  if (depts) state.departments = depts;

  const cats = await apiFetch('/api/org/categories');
  if (cats) state.categories = cats;

  const emps = await apiFetch('/api/org/employees');
  if (emps) state.employees = emps;

  const assets = await apiFetch('/api/assets');
  if (assets) state.allAssets = assets;

  populateSelectors();
}

function populateSelectors() {
  // Populate Categories
  const catSelects = [
    document.getElementById('asset-filter-category'),
    document.getElementById('reg-category')
  ];
  catSelects.forEach(sel => {
    if (!sel) return;
    const originalVal = sel.value;
    sel.innerHTML = sel.id.includes('filter') ? '<option value="">All Categories</option>' : '<option value="">-- Choose Category --</option>';
    state.categories.forEach(c => {
      sel.innerHTML += `<option value="${c.id}">${c.name}</option>`;
    });
    sel.value = originalVal;
  });

  // Populate Departments
  const deptSelects = [
    document.getElementById('asset-filter-dept'),
    document.getElementById('alloc-dept-id'),
    document.getElementById('promote-dept'),
    document.getElementById('dept-parent-id')
  ];
  deptSelects.forEach(sel => {
    if (!sel) return;
    const originalVal = sel.value;
    sel.innerHTML = sel.id.includes('filter') ? '<option value="">All Departments</option>' : (sel.id.includes('parent') ? '<option value="">-- None (Top level) --</option>' : '<option value="">-- Choose Department --</option>');
    state.departments.forEach(d => {
      sel.innerHTML += `<option value="${d.id}">${d.name}</option>`;
    });
    sel.value = originalVal;
  });

  // Populate Employees
  const empSelects = [
    document.getElementById('alloc-emp-id')
  ];
  empSelects.forEach(sel => {
    if (!sel) return;
    const originalVal = sel.value;
    sel.innerHTML = '<option value="">-- Choose Employee --</option>';
    state.employees.forEach(e => {
      sel.innerHTML += `<option value="${e.id}">${e.name} (${e.department_name || 'No Dept'})</option>`;
    });
    sel.value = originalVal;
  });

  // Populate Assets for allocation / maintenance
  const allocAssetSel = document.getElementById('alloc-asset-id');
  if (allocAssetSel) {
    allocAssetSel.innerHTML = '<option value="">-- Choose Asset --</option>';
    state.allAssets.forEach(a => {
      allocAssetSel.innerHTML += `<option value="${a.id}">${a.asset_tag} - ${a.name} [${a.status}]</option>`;
    });
  }

  const maintAssetSel = document.getElementById('maint-asset-id');
  if (maintAssetSel) {
    maintAssetSel.innerHTML = '<option value="">-- Choose Asset --</option>';
    state.allAssets.forEach(a => {
      maintAssetSel.innerHTML += `<option value="${a.id}">${a.asset_tag} - ${a.name}</option>`;
    });
  }

  // Populate Shared resources for bookings
  const bookAssetSel = document.getElementById('book-asset-id');
  if (bookAssetSel) {
    bookAssetSel.innerHTML = '<option value="">-- Choose Shared Resource --</option>';
    state.allAssets.filter(a => a.is_shared).forEach(a => {
      bookAssetSel.innerHTML += `<option value="${a.id}">${a.name} (${a.location})</option>`;
    });
  }

  // Populate Auditors select list (Admin audits cycle create)
  const auditorSel = document.getElementById('audit-auditors');
  if (auditorSel) {
    auditorSel.innerHTML = '';
    state.employees.forEach(e => {
      auditorSel.innerHTML += `<option value="${e.id}">${e.name} (${e.role.replace('_', ' ')})</option>`;
    });
  }
}

// ==================== VIEW ROUTER SYSTEM ====================
function switchView(view) {
  state.currentView = view;
  
  // Hide all sections
  document.querySelectorAll('.view-section').forEach(s => s.classList.add('d-none'));
  
  // Deactivate all sidebar items
  document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
  
  // Set current active sidebar item
  const activeItem = document.querySelector(`.sidebar-item[data-view="${view}"]`);
  if (activeItem) activeItem.classList.add('active');

  // Display targeted section
  const section = document.getElementById(`view-${view}`);
  if (section) section.classList.remove('d-none');

  // Update header text
  const viewTitleMap = {
    dashboard: 'Dashboard Overview',
    assets: 'Assets Catalog',
    allocations: 'Asset Allocations & Transfers',
    bookings: 'Shared Resource Bookings',
    maintenance: 'Maintenance Board',
    audits: 'Verification Audits',
    reports: 'Reports & Analytics',
    admin: 'Organization Setup',
    logs: 'Activity Audit Trail',
    notifications: 'Notifications Feed'
  };
  document.getElementById('current-view-title').textContent = viewTitleMap[view] || 'AssetFlow';

  // Toggle app layout container
  document.getElementById('auth-container').classList.add('d-none');
  document.getElementById('app-wrapper').classList.remove('d-none');

  // Run view initialization triggers
  if (view === 'dashboard') loadDashboardData();
  if (view === 'assets') searchAssets();
  if (view === 'allocations') loadAllocationsData();
  if (view === 'bookings') loadBookingsData();
  if (view === 'maintenance') loadMaintenanceData();
  if (view === 'audits') loadAuditsData();
  if (view === 'reports') loadAnalyticsData();
  if (view === 'admin') loadAdminData();
  if (view === 'logs') loadLogsData();
  if (view === 'notifications') loadNotificationsData();

  // Re-run icons render
  lucide.createIcons();
}

// ==================== VIEW 1: DASHBOARD OVERVIEW ====================
async function loadDashboardData() {
  const data = await apiFetch('/api/reports/dashboard');
  if (!data) return;

  // Render KPIs
  document.getElementById('kpi-avail').textContent = data.assets_available;
  document.getElementById('kpi-alloc').textContent = data.assets_allocated;
  document.getElementById('kpi-maint').textContent = data.maintenance_today;
  document.getElementById('kpi-bookings').textContent = data.active_bookings;
  document.getElementById('kpi-transfers').textContent = data.pending_transfers;
  
  // Overdue count badge
  const overdueCount = document.getElementById('overdue-count');
  overdueCount.textContent = `${data.overdue_returns_count} items`;
  
  // Overdue table body
  const tbody = document.getElementById('overdue-tbody');
  tbody.innerHTML = '';
  
  if (data.overdue_returns.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center" style="color: var(--text-muted);">No overdue returns. Good job!</td></tr>`;
  } else {
    data.overdue_returns.forEach(item => {
      tbody.innerHTML += `
        <tr>
          <td><a class="asset-details-link" data-id="${item.asset_tag}">${item.asset_tag}</a></td>
          <td><strong>${item.asset_name}</strong></td>
          <td>${item.holder_name}</td>
          <td>${new Date(item.expected_return_date).toLocaleDateString()}</td>
          <td><span class="badge badge-lost">${item.overdue_days} days overdue</span></td>
        </tr>
      `;
    });
  }
  
  // Attach detail listeners
  attachAssetDetailLinks();
}

// ==================== VIEW 2: ASSETS CATALOG ====================
async function searchAssets() {
  const search = document.getElementById('asset-filter-search').value;
  const category = document.getElementById('asset-filter-category').value;
  const status = document.getElementById('asset-filter-status').value;
  const dept = document.getElementById('asset-filter-dept').value;
  const location = document.getElementById('asset-filter-location').value;

  let query = '?';
  if (search) query += `search=${encodeURIComponent(search)}&`;
  if (category) query += `category_id=${category}&`;
  if (status) query += `status=${status}&`;
  if (dept) query += `department_id=${dept}&`;
  if (location) query += `location=${encodeURIComponent(location)}&`;

  const assets = await apiFetch(`/api/assets${query}`);
  if (!assets) return;

  // Save to state
  state.allAssets = assets;

  const tbody = document.getElementById('assets-tbody');
  tbody.innerHTML = '';

  if (assets.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center">No assets found matching filters.</td></tr>`;
    return;
  }

  const isManagerOrAdmin = ['admin', 'asset_manager'].includes(state.user.role);

  assets.forEach(a => {
    const holder = a.current_holder_name ? `${a.current_holder_name} (${a.department_name || 'No Dept'})` : 'N/A';
    
    // Status Badge classes
    let statusClass = 'badge-available';
    if (a.status === 'Allocated') statusClass = 'badge-allocated';
    if (a.status === 'Reserved') statusClass = 'badge-reserved';
    if (a.status === 'Under Maintenance') statusClass = 'badge-maintenance';
    if (['Lost', 'Damaged', 'Broken'].includes(a.status)) statusClass = 'badge-lost';
    if (['Retired', 'Disposed'].includes(a.status)) statusClass = 'badge-retired';

    // Actions columns
    let actionButtons = `<button class="btn btn-secondary btn-sm asset-details-btn" data-id="${a.id}"><i data-lucide="eye" style="width: 14px; height: 14px;"></i> View</button> `;
    if (isManagerOrAdmin) {
      if (a.status === 'Allocated') {
        actionButtons += `<button class="btn btn-success btn-sm asset-return-btn" data-id="${a.id}"><i data-lucide="corner-down-left" style="width: 14px; height: 14px;"></i> Return</button>`;
      } else if (a.status === 'Available') {
        actionButtons += `<button class="btn btn-sm asset-allocate-btn" data-id="${a.id}"><i data-lucide="user-check" style="width: 14px; height: 14px;"></i> Allocate</button>`;
      }
    }

    tbody.innerHTML += `
      <tr>
        <td><a class="asset-details-link" data-id="${a.asset_tag}">${a.asset_tag}</a></td>
        <td><strong>${a.name}</strong> ${a.is_shared ? '<span class="badge badge-reserved" style="font-size: 8px; padding: 2px 4px; margin-left: 4px;">Shared</span>' : ''}</td>
        <td>${a.category_name}</td>
        <td><span class="badge ${statusClass}">${a.status}</span></td>
        <td>${a.condition}</td>
        <td>${a.location}</td>
        <td>${holder}</td>
        <td>
          <div class="flex gap-2">${actionButtons}</div>
        </td>
      </tr>
    `;
  });

  // Attach button triggers
  document.querySelectorAll('.asset-details-btn').forEach(btn => {
    btn.addEventListener('click', () => openAssetDetailsModal(btn.dataset.id));
  });

  document.querySelectorAll('.asset-return-btn').forEach(btn => {
    btn.addEventListener('click', () => openReturnAssetModal(btn.dataset.id));
  });

  document.querySelectorAll('.asset-allocate-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      switchView('allocations');
      document.getElementById('alloc-asset-id').value = btn.dataset.id;
      // Trigger change warning check
      document.getElementById('alloc-asset-id').dispatchEvent(new Event('change'));
    });
  });

  attachAssetDetailLinks();
  lucide.createIcons();
}

function attachAssetDetailLinks() {
  document.querySelectorAll('.asset-details-link').forEach(link => {
    link.addEventListener('click', async (e) => {
      e.preventDefault();
      const asset = state.allAssets.find(a => a.asset_tag === link.dataset.id);
      if (asset) openAssetDetailsModal(asset.id);
    });
  });
}

// ==================== VIEW 3: ALLOCATIONS & TRANSFERS ====================
async function loadAllocationsData() {
  // Re-load list of assets to populate selector correctly
  const assets = await apiFetch('/api/assets');
  if (assets) {
    state.allAssets = assets;
    populateSelectors();
  }

  // Fetch transfer requests
  const transfers = await apiFetch('/api/allocations/transfers');
  const tbody = document.getElementById('transfers-tbody');
  tbody.innerHTML = '';

  if (!transfers || transfers.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center" style="color: var(--text-muted);">No transfer requests found.</td></tr>`;
    return;
  }

  const isHeadOrManager = ['admin', 'asset_manager', 'department_head'].includes(state.user.role);

  transfers.forEach(t => {
    let statusClass = 'badge-pending';
    if (t.status === 'Approved') statusClass = 'badge-approved';
    if (t.status === 'Rejected') statusClass = 'badge-rejected';

    let actions = 'N/A';
    if (t.status === 'Pending') {
      if (isHeadOrManager) {
        actions = `
          <button class="btn btn-success btn-sm btn-approve-transfer" data-id="${t.id}"><i data-lucide="check"></i> Approve</button>
          <button class="btn btn-danger btn-sm btn-reject-transfer" data-id="${t.id}"><i data-lucide="x"></i> Reject</button>
        `;
      } else {
        actions = '<span style="color: var(--text-dark);">Awaiting Manager</span>';
      }
    }

    tbody.innerHTML += `
      <tr>
        <td><strong>${t.asset_name}</strong> (${t.asset_tag})</td>
        <td>${t.from_employee_name}</td>
        <td>${t.to_employee_name}</td>
        <td><em>"${t.reason}"</em></td>
        <td>${new Date(t.created_at).toLocaleDateString()}</td>
        <td><span class="badge ${statusClass}">${t.status}</span></td>
        <td>
          <div class="flex gap-2" style="font-size: 11px;">${actions}</div>
        </td>
      </tr>
    `;
  });

  // Wire action handlers
  document.querySelectorAll('.btn-approve-transfer').forEach(btn => {
    btn.addEventListener('click', () => handleTransferAction(btn.dataset.id, 'approve'));
  });

  document.querySelectorAll('.btn-reject-transfer').forEach(btn => {
    btn.addEventListener('click', () => handleTransferAction(btn.dataset.id, 'reject'));
  });

  lucide.createIcons();
}

async function handleTransferAction(id, action) {
  const result = await apiFetch(`/api/allocations/transfers/${id}/${action}`, {
    method: 'PUT'
  });
  if (result) {
    showToast('Success', `Transfer request ${action}d!`, 'success');
    loadAllocationsData();
    loadDashboardData();
  }
}

// Double Allocation Block Validation on Change
const allocAssetInput = document.getElementById('alloc-asset-id');
if (allocAssetInput) {
  allocAssetInput.addEventListener('change', () => {
    const selectedAssetId = parseInt(allocAssetInput.value);
    const alertBox = document.getElementById('double-allocation-alert');
    const submitBtn = document.getElementById('btn-submit-alloc');
    const transferBtn = document.getElementById('btn-submit-transfer-req');

    if (!selectedAssetId) {
      alertBox.style.display = 'none';
      submitBtn.style.display = 'inline-flex';
      submitBtn.disabled = false;
      transferBtn.style.display = 'none';
      return;
    }

    const asset = state.allAssets.find(a => a.id === selectedAssetId);
    if (asset && asset.status !== 'Available') {
      // Double allocation conflict triggered
      const holder = asset.current_holder_name || 'Department-wide';
      const dept = asset.department_name || 'N/A';
      
      alertBox.style.display = 'block';
      alertBox.textContent = `Double Allocation Warning: Already Allocated to ${holder} (${dept}). Direct re-allocation is blocked - submit a transfer request below.`;
      
      submitBtn.style.display = 'none';
      transferBtn.style.display = 'inline-flex';
    } else {
      alertBox.style.display = 'none';
      submitBtn.style.display = 'inline-flex';
      submitBtn.disabled = false;
      transferBtn.style.display = 'none';
    }
  });
}

// ==================== VIEW 4: SHARED RESOURCE BOOKINGS ====================
async function loadBookingsData() {
  const bookings = await apiFetch('/api/bookings');
  const container = document.getElementById('bookings-schedule-container');
  container.innerHTML = '';

  if (!bookings || bookings.length === 0) {
    container.innerHTML = `<div class="text-center" style="padding: 20px; color: var(--text-muted);">No active bookings scheduled.</div>`;
    return;
  }

  bookings.forEach(b => {
    let statusClass = 'badge-pending';
    if (b.status === 'Completed') statusClass = 'badge-available';
    if (b.status === 'Cancelled') statusClass = 'badge-retired';
    if (b.status === 'Ongoing') statusClass = 'badge-allocated';

    // Show cancel button only for user's bookings, or managers
    const canCancel = (state.user.id === b.booked_by_id || ['admin', 'asset_manager'].includes(state.user.role)) && !['Completed', 'Cancelled'].includes(b.status);
    const cancelBtn = canCancel ? `<button class="btn btn-secondary btn-sm cancel-booking-btn" data-id="${b.id}"><i data-lucide="calendar-x" style="width: 14px; height: 14px;"></i> Cancel</button>` : '';

    container.innerHTML += `
      <div class="booking-slot">
        <div class="booking-slot-info">
          <div class="booking-slot-title">${b.asset_name} (${b.asset_tag})</div>
          <div class="booking-slot-time">
            <i data-lucide="clock" style="width: 12px; height: 12px; display: inline; vertical-align: middle;"></i>
            <strong>${new Date(b.start_time).toLocaleString()}</strong> to <strong>${new Date(b.end_time).toLocaleString()}</strong>
          </div>
          <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Booked by: <strong>${b.booked_by_name}</strong></div>
        </div>
        <div class="flex align-center gap-2">
          <span class="badge ${statusClass}">${b.status}</span>
          ${cancelBtn}
        </div>
      </div>
    `;
  });

  document.querySelectorAll('.cancel-booking-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const ok = confirm('Are you sure you want to cancel this booking?');
      if (ok) {
        const res = await apiFetch(`/api/bookings/${btn.dataset.id}/cancel`, { method: 'PUT' });
        if (res) {
          showToast('Cancelled', 'Resource booking has been cancelled.', 'info');
          loadBookingsData();
        }
      }
    });
  });

  lucide.createIcons();
}

// ==================== VIEW 5: MAINTENANCE & REPAIR BOARD ====================
async function loadMaintenanceData() {
  const tickets = await apiFetch('/api/maintenance');
  
  // Clear Column lists
  document.getElementById('kanban-pending').innerHTML = '';
  document.getElementById('kanban-assigned').innerHTML = '';
  document.getElementById('kanban-progress').innerHTML = '';
  document.getElementById('kanban-resolved').innerHTML = '';
  
  // Counts
  const counts = { Pending: 0, 'Approved': 0, 'Technician Assigned': 0, 'In Progress': 0, Resolved: 0, Rejected: 0 };
  
  if (!tickets) return;

  const isManagerOrAdmin = ['admin', 'asset_manager'].includes(state.user.role);

  tickets.forEach(t => {
    counts[t.status] = (counts[t.status] || 0) + 1;

    let priorityBadge = `<span class="badge" style="font-size: 9px; padding: 2px 6px; background: rgba(255,255,255,0.08); color: var(--text-muted);">${t.priority}</span>`;
    if (t.priority === 'High') priorityBadge = `<span class="badge badge-warning" style="font-size: 9px; padding: 2px 6px;">${t.priority}</span>`;
    if (t.priority === 'Critical') priorityBadge = `<span class="badge badge-lost" style="font-size: 9px; padding: 2px 6px;">${t.priority}</span>`;

    const htmlCard = `
      <div class="kanban-card maint-ticket-card" data-id="${t.id}">
        <div class="flex justify-between align-center mb-2">
          <span style="font-size: 11px; font-weight: bold; color: var(--primary);">${t.asset_tag}</span>
          ${priorityBadge}
        </div>
        <div class="kanban-card-title">${t.asset_name}</div>
        <div class="kanban-card-desc">${t.description}</div>
        <div class="kanban-card-footer">
          <span style="color: var(--text-dark);">By: ${t.reporter_name}</span>
          <span style="font-style: italic;">${t.technician_name ? `Tech: ${t.technician_name}` : 'Unassigned'}</span>
        </div>
      </div>
    `;

    // Append to column
    if (t.status === 'Pending') {
      document.getElementById('kanban-pending').innerHTML += htmlCard;
    } else if (t.status === 'Approved' || t.status === 'Technician Assigned') {
      document.getElementById('kanban-assigned').innerHTML += htmlCard;
    } else if (t.status === 'In Progress') {
      document.getElementById('kanban-progress').innerHTML += htmlCard;
    } else if (t.status === 'Resolved' || t.status === 'Rejected') {
      document.getElementById('kanban-resolved').innerHTML += htmlCard;
    }
  });

  // Update counts
  document.getElementById('col-pending-count').textContent = counts['Pending'] || 0;
  document.getElementById('col-assigned-count').textContent = (counts['Approved'] || 0) + (counts['Technician Assigned'] || 0);
  document.getElementById('col-progress-count').textContent = counts['In Progress'] || 0;
  document.getElementById('col-resolved-count').textContent = (counts['Resolved'] || 0) + (counts['Rejected'] || 0);

  // Wire manager click events
  if (isManagerOrAdmin) {
    document.querySelectorAll('.maint-ticket-card').forEach(card => {
      card.addEventListener('click', () => openManageMaintenanceModal(card.dataset.id));
    });
  }

  lucide.createIcons();
}

async function openManageMaintenanceModal(id) {
  const tickets = await apiFetch('/api/maintenance');
  const ticket = tickets.find(t => t.id === parseInt(id));
  if (!ticket) return;

  document.getElementById('manage-maint-id-hidden').value = ticket.id;
  document.getElementById('manage-maint-asset').textContent = `${ticket.asset_name} (${ticket.asset_tag})`;
  document.getElementById('manage-maint-reporter').textContent = ticket.reporter_name;
  document.getElementById('manage-maint-desc').textContent = ticket.description;
  document.getElementById('manage-maint-status').value = ticket.status;
  document.getElementById('manage-maint-tech').value = ticket.technician_name || '';
  document.getElementById('manage-maint-notes').value = ticket.resolution_notes || '';

  const modal = document.getElementById('modal-manage-maintenance');
  modal.classList.add('active');
}

// ==================== VIEW 6: AUDIT CYCLES ====================
async function loadAuditsData() {
  const cycles = await apiFetch('/api/audits/cycles');
  const tbody = document.getElementById('audits-tbody');
  tbody.innerHTML = '';

  // Show cycle create form if admin
  const isAdmin = state.user.role === 'admin';
  document.getElementById('admin-audit-card').style.display = isAdmin ? 'block' : 'none';

  if (!cycles || cycles.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center" style="color: var(--text-muted);">No audit cycles launched.</td></tr>`;
    return;
  }

  cycles.forEach(c => {
    let statusClass = 'badge-pending';
    if (c.status === 'Closed') statusClass = 'badge-retired';
    if (c.status === 'Active') statusClass = 'badge-active';

    const scope = `${c.scope_type} ${c.scope_value ? `(${c.scope_value})` : ''}`;
    
    // Actions button
    let actionBtn = `<button class="btn btn-secondary btn-sm workspace-audit-btn" data-id="${c.id}"><i data-lucide="clipboard-list" style="width: 14px; height: 14px;"></i> Workspace</button>`;

    tbody.innerHTML += `
      <tr>
        <td><strong>${c.name}</strong></td>
        <td>${scope}</td>
        <td>${c.auditor_names.join(', ') || 'None'}</td>
        <td><span class="badge ${statusClass}">${c.status}</span></td>
        <td>${actionBtn}</td>
      </tr>
    `;
  });

  document.querySelectorAll('.workspace-audit-btn').forEach(btn => {
    btn.addEventListener('click', () => openAuditorWorkspace(btn.dataset.id));
  });

  lucide.createIcons();
}

async function openAuditorWorkspace(cycleId) {
  const cycles = await apiFetch('/api/audits/cycles');
  const cycle = cycles.find(c => c.id === parseInt(cycleId));
  if (!cycle) return;

  // Toggle View panels
  document.getElementById('audit-cycles-col').style.display = 'none';
  document.getElementById('admin-audit-card').style.display = 'none';
  
  const workspaceCard = document.getElementById('auditor-workspace-card');
  workspaceCard.style.display = 'block';

  document.getElementById('active-audit-title').textContent = `${cycle.name} [Status: ${cycle.status}]`;

  // Determine if current user can close this cycle (Admin, and cycle active)
  const closeBtn = document.getElementById('btn-close-audit-cycle');
  if (state.user.role === 'admin' && cycle.status === 'Active') {
    closeBtn.style.display = 'inline-flex';
    closeBtn.dataset.id = cycle.id;
  } else {
    closeBtn.style.display = 'none';
  }

  // Load audit records
  loadAuditRecords(cycle.id, cycle.status);
}

async function loadAuditRecords(cycleId, cycleStatus) {
  const records = await apiFetch(`/api/audits/cycles/${cycleId}/records`);
  const tbody = document.getElementById('audit-records-tbody');
  tbody.innerHTML = '';

  if (!records || records.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center">No assets found in scope.</td></tr>`;
    return;
  }

  records.forEach(r => {
    let badgeClass = 'badge-pending';
    if (r.verification_status === 'Verified') badgeClass = 'badge-available';
    if (r.verification_status === 'Missing') badgeClass = 'badge-lost';
    if (r.verification_status === 'Damaged') badgeClass = 'badge-broken';

    // Verification controls: show inputs if active cycle
    let controls = '<span style="color: var(--text-dark);">Cycle Locked</span>';
    if (cycleStatus === 'Active') {
      controls = `
        <div class="flex gap-2">
          <button class="btn btn-success btn-sm btn-verify-record" data-id="${r.id}" data-status="Verified">Verify</button>
          <button class="btn btn-warning btn-sm btn-verify-record" data-id="${r.id}" data-status="Damaged">Damage</button>
          <button class="btn btn-danger btn-sm btn-verify-record" data-id="${r.id}" data-status="Missing">Missing</button>
        </div>
      `;
    }

    tbody.innerHTML += `
      <tr>
        <td><strong>${r.asset_tag}</strong></td>
        <td>${r.asset_name}</td>
        <td>${r.asset_location}</td>
        <td>${r.expected_holder_name || 'Unassigned'}</td>
        <td><span class="badge ${badgeClass}">${r.verification_status}</span></td>
        <td>${r.auditor_name ? `${r.auditor_name} (${new Date(r.audited_at).toLocaleDateString()})` : 'Pending'}</td>
        <td>${controls}</td>
      </tr>
    `;
  });

  // Attach verifier buttons
  document.querySelectorAll('.btn-verify-record').forEach(btn => {
    btn.addEventListener('click', async () => {
      const noteStr = prompt('Enter audit observations/notes (optional):');
      const payload = {
        verification_status: btn.dataset.status,
        notes: noteStr || ''
      };
      const res = await apiFetch(`/api/audits/records/${btn.dataset.id}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      });
      if (res) {
        showToast('Audited', `Logged verification: ${btn.dataset.status}`, 'success');
        loadAuditRecords(cycleId, cycleStatus);
      }
    });
  });

  lucide.createIcons();
}

// Close Audit cycle trigger
const btnCloseAudit = document.getElementById('btn-close-audit-cycle');
if (btnCloseAudit) {
  btnCloseAudit.addEventListener('click', async () => {
    const cycleId = btnCloseAudit.dataset.id;
    const ok = confirm('CLOSING AUDIT CYCLE: This will lock the audit cycle and automatically transition missing items to "Lost" status and damaged items to "Damaged" status. Continue?');
    if (ok) {
      const res = await apiFetch(`/api/audits/cycles/${cycleId}/close`, { method: 'POST' });
      if (res) {
        showToast('Audit Cycle Closed', 'Cycle is locked. Asset directory statuses have been updated.', 'success');
        document.getElementById('btn-back-to-audits').click();
      }
    }
  });
}

const btnBackAudits = document.getElementById('btn-back-to-audits');
if (btnBackAudits) {
  btnBackAudits.addEventListener('click', () => {
    document.getElementById('audit-cycles-col').style.display = 'block';
    // Restore admin create card if they are admin
    const isAdmin = state.user.role === 'admin';
    document.getElementById('admin-audit-card').style.display = isAdmin ? 'block' : 'none';
    document.getElementById('auditor-workspace-card').style.display = 'none';
    loadAuditsData();
  });
}

// ==================== VIEW 7: REPORTS & ANALYTICS ====================
async function loadAnalyticsData() {
  const data = await apiFetch('/api/reports/analytics');
  if (!data) return;

  // Setup CSV Export link
  const storedToken = state.token || localStorage.getItem('token');
  document.getElementById('btn-export-csv').href = `${API_BASE}/api/reports/export?token=${storedToken}`;
  document.getElementById('btn-export-csv').addEventListener('click', (e) => {
    e.preventDefault();
    window.open(`${API_BASE}/api/reports/export?token=${storedToken}`);
  });

  // Render analytics charts
  renderUtilizationChart(data.utilization_summary);
  renderMaintenanceChart(data.maintenance_by_category);

  // Render Most-Used shared resources
  const mostUsedTbody = document.getElementById('reports-most-used-tbody');
  mostUsedTbody.innerHTML = '';
  if (data.most_used_assets.length === 0) {
    mostUsedTbody.innerHTML = `<tr><td colspan="3" class="text-center">No resources booked yet.</td></tr>`;
  } else {
    data.most_used_assets.forEach(a => {
      mostUsedTbody.innerHTML += `
        <tr>
          <td><a class="asset-details-link" data-id="${a.asset_tag}">${a.asset_tag}</a></td>
          <td><strong>${a.asset_name}</strong></td>
          <td><span class="badge badge-reserved">${a.count} bookings</span></td>
        </tr>
      `;
    });
  }

  // Render Idle assets
  const idleTbody = document.getElementById('reports-idle-tbody');
  idleTbody.innerHTML = '';
  if (data.idle_assets.length === 0) {
    idleTbody.innerHTML = `<tr><td colspan="3" class="text-center">No idle assets. All assets are currently active.</td></tr>`;
  } else {
    data.idle_assets.forEach(a => {
      idleTbody.innerHTML += `
        <tr>
          <td><a class="asset-details-link" data-id="${a.asset_tag}">${a.asset_tag}</a></td>
          <td><strong>${a.asset_name}</strong></td>
          <td><span class="badge badge-maintenance">${a.idle_days} days unused</span></td>
        </tr>
      `;
    });
  }

  // Render Retirement and Service alerts
  const retirementTbody = document.getElementById('reports-retirement-tbody');
  retirementTbody.innerHTML = '';
  if (data.assets_nearing_retirement.length === 0) {
    retirementTbody.innerHTML = `<tr><td colspan="5" class="text-center">No critical retirement alerts found.</td></tr>`;
  } else {
    data.assets_nearing_retirement.forEach(a => {
      retirementTbody.innerHTML += `
        <tr>
          <td><a class="asset-details-link" data-id="${a.asset_tag}">${a.asset_tag}</a></td>
          <td><strong>${a.asset_name}</strong></td>
          <td>${new Date(a.acquisition_date).toLocaleDateString()}</td>
          <td><span class="badge ${a.condition === 'Good' ? 'badge-available' : 'badge-lost'}">${a.condition}</span></td>
          <td><span style="color: #fca5a5; font-weight: 500;">${a.detail.split(' : ')[1] || 'Retirement pending'}</span></td>
        </tr>
      `;
    });
  }

  attachAssetDetailLinks();
}

function renderUtilizationChart(summary) {
  // Clear existing
  if (state.charts.utilization) {
    state.charts.utilization.destroy();
  }

  const labels = Object.keys(summary);
  const values = Object.values(summary);

  const options = {
    chart: {
      type: 'donut',
      height: 250,
      foreColor: '#94a3b8'
    },
    series: values,
    labels: labels,
    colors: ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#6b7280'],
    theme: {
      mode: 'dark'
    },
    legend: {
      position: 'bottom'
    },
    stroke: {
      show: false
    }
  };

  const chart = new ApexCharts(document.querySelector("#chart-utilization"), options);
  chart.render();
  state.charts.utilization = chart;
}

function renderMaintenanceChart(summary) {
  // Clear existing
  if (state.charts.maintenance) {
    state.charts.maintenance.destroy();
  }

  const categories = Object.keys(summary);
  const values = Object.values(summary);

  const options = {
    chart: {
      type: 'bar',
      height: 250,
      foreColor: '#94a3b8',
      toolbar: { show: false }
    },
    series: [{
      name: 'Tickets Raised',
      data: values
    }],
    xaxis: {
      categories: categories
    },
    colors: ['#8b5cf6'],
    theme: {
      mode: 'dark'
    },
    plotOptions: {
      bar: {
        borderRadius: 6,
        columnWidth: '40%'
      }
    }
  };

  const chart = new ApexCharts(document.querySelector("#chart-maintenance"), options);
  chart.render();
  state.charts.maintenance = chart;
}

// ==================== VIEW 8: ORGANIZATION SETUP (ADMIN) ====================
async function loadAdminData() {
  loadDepartmentsTab();
  loadCategoriesTab();
  loadEmployeesTab();
}

// Tab A: Departments
async function loadDepartmentsTab() {
  const depts = await apiFetch('/api/org/departments');
  if (depts) state.departments = depts;

  const tbody = document.getElementById('admin-depts-tbody');
  tbody.innerHTML = '';

  state.departments.forEach(d => {
    let statusClass = d.status === 'Active' ? 'badge-available' : 'badge-retired';
    tbody.innerHTML += `
      <tr>
        <td>${d.id}</td>
        <td><strong>${d.name}</strong></td>
        <td>${d.head_name || '<span style="color: var(--text-dark);">Unassigned</span>'}</td>
        <td>${state.departments.find(p => p.id === d.parent_department_id)?.name || 'None'}</td>
        <td><span class="badge ${statusClass}">${d.status}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm btn-deactivate-dept" data-id="${d.id}" data-status="${d.status}">
            ${d.status === 'Active' ? 'Deactivate' : 'Activate'}
          </button>
        </td>
      </tr>
    `;
  });

  document.querySelectorAll('.btn-deactivate-dept').forEach(btn => {
    btn.addEventListener('click', async () => {
      const newStatus = btn.dataset.status === 'Active' ? 'Inactive' : 'Active';
      const res = await apiFetch(`/api/org/departments/${btn.dataset.id}`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus })
      });
      if (res) {
        showToast('Success', `Department marked ${newStatus}`, 'success');
        loadDepartmentsTab();
        loadSupportingData();
      }
    });
  });
}

// Tab B: Categories
async function loadCategoriesTab() {
  const cats = await apiFetch('/api/org/categories');
  if (cats) state.categories = cats;

  const tbody = document.getElementById('admin-cats-tbody');
  tbody.innerHTML = '';

  state.categories.forEach(c => {
    tbody.innerHTML += `
      <tr>
        <td>${c.id}</td>
        <td><strong>${c.name}</strong></td>
      </tr>
    `;
  });
}

// Tab C: Employee Promotion Directory
async function loadEmployeesTab() {
  const emps = await apiFetch('/api/org/employees');
  if (emps) state.employees = emps;

  const tbody = document.getElementById('admin-employees-tbody');
  tbody.innerHTML = '';

  state.employees.forEach(e => {
    let statusClass = e.status === 'Active' ? 'badge-available' : 'badge-retired';
    let roleClass = 'badge-retired';
    if (e.role === 'admin') roleClass = 'badge-lost';
    if (e.role === 'asset_manager') roleClass = 'badge-allocated';
    if (e.role === 'department_head') roleClass = 'badge-reserved';

    tbody.innerHTML += `
      <tr>
        <td><strong>${e.name}</strong></td>
        <td>${e.email}</td>
        <td>${e.department_name || '<span style="color: var(--text-dark);">Unassigned</span>'}</td>
        <td><span class="badge ${roleClass}">${e.role.replace('_', ' ')}</span></td>
        <td><span class="badge ${statusClass}">${e.status}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm btn-promote-emp" data-id="${e.id}">
            <i data-lucide="shield-alert" style="width: 14px; height: 14px;"></i> Update Profile / Role
          </button>
        </td>
      </tr>
    `;
  });

  document.querySelectorAll('.btn-promote-emp').forEach(btn => {
    btn.addEventListener('click', () => openPromoteEmployeeModal(btn.dataset.id));
  });

  lucide.createIcons();
}

async function openPromoteEmployeeModal(id) {
  const emp = state.employees.find(e => e.id === parseInt(id));
  if (!emp) return;

  document.getElementById('promote-emp-id-hidden').value = emp.id;
  document.getElementById('promote-emp-name').textContent = emp.name;
  document.getElementById('promote-role').value = emp.role;
  document.getElementById('promote-dept').value = emp.department_id || '';
  document.getElementById('promote-status').value = emp.status;

  const modal = document.getElementById('modal-promote-employee');
  modal.classList.add('active');
}

// ==================== VIEW 9: NOTIFICATIONS FEED ====================
async function updateNotificationBadge() {
  const notifs = await apiFetch('/api/notifications');
  if (!notifs) return;

  const unread = notifs.filter(n => !n.is_read).length;
  const badge = document.getElementById('notif-count');
  
  if (unread > 0) {
    badge.textContent = unread;
    badge.classList.remove('d-none');
  } else {
    badge.classList.add('d-none');
  }
}

async function loadNotificationsData() {
  const filter = document.getElementById('notif-filter').value;
  const notifs = await apiFetch(`/api/notifications?filter_type=${filter}`);
  const container = document.getElementById('notifications-list-container');
  container.innerHTML = '';

  if (!notifs || notifs.length === 0) {
    container.innerHTML = `<div class="text-center" style="padding: 20px; color: var(--text-muted);">No notifications found.</div>`;
    return;
  }

  notifs.forEach(n => {
    let unreadClass = n.is_read ? '' : 'unread';
    let icon = 'bell';
    if (n.type.includes('Assigned')) icon = 'user-check';
    if (n.type.includes('Maintenance')) icon = 'tool';
    if (n.type.includes('Booking')) icon = 'calendar';
    if (n.type.includes('Transfer')) icon = 'git-pull-request';
    if (n.type.includes('Overdue')) icon = 'alert-triangle';
    if (n.type.includes('Audit')) icon = 'clipboard-check';

    const markReadBtn = n.is_read ? '' : `<button class="btn btn-secondary btn-sm btn-mark-read" data-id="${n.id}">Mark Read</button>`;

    container.innerHTML += `
      <div class="notification-item ${unreadClass}">
        <div class="notification-icon">
          <i data-lucide="${icon}" style="width: 18px; height: 18px;"></i>
        </div>
        <div class="notification-content">
          <div class="notification-title">${n.title}</div>
          <div class="notification-desc">${n.message}</div>
          <div class="notification-time">${new Date(n.created_at).toLocaleString()}</div>
        </div>
        <div>
          ${markReadBtn}
        </div>
      </div>
    `;
  });

  document.querySelectorAll('.btn-mark-read').forEach(btn => {
    btn.addEventListener('click', async () => {
      const res = await apiFetch(`/api/notifications/${btn.dataset.id}/read`, { method: 'PUT' });
      if (res) {
        loadNotificationsData();
        updateNotificationBadge();
      }
    });
  });

  lucide.createIcons();
}

// ==================== VIEW 10: SYSTEM LOGS ====================
async function loadLogsData() {
  const logs = await apiFetch('/api/notifications/activities');
  const tbody = document.getElementById('logs-tbody');
  tbody.innerHTML = '';

  if (!logs || logs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center">No logs found.</td></tr>`;
    return;
  }

  logs.forEach(l => {
    tbody.innerHTML += `
      <tr>
        <td>#${l.id}</td>
        <td><strong>${l.actor_name}</strong></td>
        <td><span class="badge badge-reserved" style="font-size: 10px;">${l.action}</span></td>
        <td><em>${l.details}</em></td>
        <td>${new Date(l.created_at).toLocaleString()}</td>
      </tr>
    `;
  });
}

// ==================== ASSET DETAILS & HISTORY MODAL ====================
async function openAssetDetailsModal(id) {
  const data = await apiFetch(`/api/assets/${id}`);
  if (!data) return;

  const a = data.asset;
  
  // Fill details fields
  document.getElementById('details-asset-tag').textContent = `Asset Details: ${a.asset_tag}`;
  document.getElementById('details-asset-name').textContent = a.name;
  document.getElementById('details-category').textContent = a.category_name;
  document.getElementById('details-serial').textContent = a.serial_number;
  document.getElementById('details-status').textContent = a.status;
  document.getElementById('details-condition').textContent = a.condition;
  document.getElementById('details-location').textContent = a.location;
  document.getElementById('details-cost').textContent = `$${a.acquisition_cost.toFixed(2)}`;
  document.getElementById('details-date').textContent = new Date(a.acquisition_date).toLocaleDateString();
  document.getElementById('details-holder').textContent = a.current_holder_name ? `${a.current_holder_name} (${a.department_name || 'No Dept'})` : 'Unallocated';

  // QR Code Rendering via public API
  const qrImg = document.getElementById('details-qr-img');
  qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(a.qr_code)}`;
  document.getElementById('details-qr-text').textContent = a.qr_code;

  // Toggle quick action buttons for Managers
  const detailsQuickActions = document.getElementById('details-quick-actions');
  const btnDetailAlloc = document.getElementById('btn-details-allocate');
  const btnDetailReturn = document.getElementById('btn-details-return');
  
  const isManagerOrAdmin = ['admin', 'asset_manager'].includes(state.user.role);
  if (isManagerOrAdmin) {
    detailsQuickActions.style.display = 'flex';
    if (a.status === 'Available') {
      btnDetailAlloc.style.display = 'inline-flex';
      btnDetailAlloc.onclick = () => {
        closeAllModals();
        switchView('allocations');
        document.getElementById('alloc-asset-id').value = a.id;
        document.getElementById('alloc-asset-id').dispatchEvent(new Event('change'));
      };
      btnDetailReturn.style.display = 'none';
    } else if (a.status === 'Allocated') {
      btnDetailAlloc.style.display = 'none';
      btnDetailReturn.style.display = 'inline-flex';
      btnDetailReturn.onclick = () => {
        closeAllModals();
        openReturnAssetModal(a.id);
      };
    } else {
      detailsQuickActions.style.display = 'none';
    }
  } else {
    detailsQuickActions.style.display = 'none';
  }

  // Populate history tables
  // 1. Allocation history
  const allocTbody = document.getElementById('details-alloc-history-tbody');
  allocTbody.innerHTML = '';
  if (data.allocation_history.length === 0) {
    allocTbody.innerHTML = `<tr><td colspan="6" class="text-center" style="color: var(--text-dark);">No allocation history logs.</td></tr>`;
  } else {
    data.allocation_history.forEach(hist => {
      const returnDate = hist.returned_at ? new Date(hist.returned_at).toLocaleDateString() : '<span style="color: var(--warning); font-weight: bold;">Active</span>';
      allocTbody.innerHTML += `
        <tr>
          <td><strong>${hist.employee_name || 'N/A'}</strong></td>
          <td>${hist.department_name || 'N/A'}</td>
          <td>${new Date(hist.allocated_at).toLocaleDateString()}</td>
          <td>${returnDate}</td>
          <td>${hist.return_condition || 'N/A'}</td>
          <td><small>${hist.check_in_notes || 'N/A'}</small></td>
        </tr>
      `;
    });
  }

  // 2. Maintenance history
  const maintTbody = document.getElementById('details-maint-history-tbody');
  maintTbody.innerHTML = '';
  if (data.maintenance_history.length === 0) {
    maintTbody.innerHTML = `<tr><td colspan="6" class="text-center" style="color: var(--text-dark);">No maintenance history logs.</td></tr>`;
  } else {
    data.maintenance_history.forEach(m => {
      maintTbody.innerHTML += `
        <tr>
          <td><strong>${m.description}</strong></td>
          <td>${m.priority}</td>
          <td>${m.reporter_name}</td>
          <td>${m.status}</td>
          <td>${m.technician_name || 'N/A'}</td>
          <td><small>${m.resolution_notes || 'N/A'}</small></td>
        </tr>
      `;
    });
  }

  // Set default tabs
  document.getElementById('btn-tab-allocation-history').click();

  const modal = document.getElementById('modal-asset-details');
  modal.classList.add('active');
}

// Return Check-in modal
async function openReturnAssetModal(assetId) {
  const asset = state.allAssets.find(a => a.id === parseInt(assetId));
  if (!asset) return;

  document.getElementById('return-asset-id-hidden').value = asset.id;
  document.getElementById('return-asset-prompt').innerHTML = `Please fill in check-in parameters for asset <strong>${asset.name} (${asset.asset_tag})</strong>.`;
  document.getElementById('ret-condition').value = asset.condition;
  document.getElementById('ret-notes').value = '';

  const modal = document.getElementById('modal-return-asset');
  modal.classList.add('active');
}

// Helper to close all modal overlays
function closeAllModals() {
  document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
}

// ==================== EVENT LISTENERS SETUP ====================
document.addEventListener('DOMContentLoaded', () => {
  // Validate token login
  validateSession();

  // Sidebar navigation trigger
  document.querySelectorAll('.sidebar-item').forEach(item => {
    item.addEventListener('click', () => {
      const view = item.dataset.view;
      if (view) switchView(view);
    });
  });

  // Topbar notification trigger
  document.getElementById('bell-icon').addEventListener('click', () => {
    switchView('notifications');
  });

  // Logout Trigger
  document.getElementById('btn-logout').addEventListener('click', logout);

  // Auth Card switching
  document.getElementById('show-signup').addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('login-card').classList.add('d-none');
    document.getElementById('signup-card').classList.remove('d-none');
  });
  document.getElementById('show-login').addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('signup-card').classList.add('d-none');
    document.getElementById('login-card').classList.remove('d-none');
  });

  // Auth Forms Submission
  document.getElementById('login-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const pass = document.getElementById('login-password').value;
    login(email, pass);
  });

  document.getElementById('signup-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const name = document.getElementById('signup-name').value;
    const email = document.getElementById('signup-email').value;
    const pass = document.getElementById('signup-password').value;
    signup(name, email, pass);
  });

  // Modal Cancel/Close buttons
  document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      closeAllModals();
    });
  });

  // Assets view filters submit
  document.getElementById('btn-search-assets').addEventListener('click', searchAssets);

  // Asset Details Tab controllers
  document.getElementById('btn-tab-allocation-history').addEventListener('click', () => {
    document.getElementById('btn-tab-allocation-history').classList.add('active');
    document.getElementById('btn-tab-maintenance-history').classList.remove('active');
    document.getElementById('panel-allocation-history').classList.remove('d-none');
    document.getElementById('panel-maintenance-history').classList.add('d-none');
  });

  document.getElementById('btn-tab-maintenance-history').addEventListener('click', () => {
    document.getElementById('btn-tab-allocation-history').classList.remove('active');
    document.getElementById('btn-tab-maintenance-history').classList.add('active');
    document.getElementById('panel-allocation-history').classList.add('d-none');
    document.getElementById('panel-maintenance-history').classList.remove('d-none');
  });

  // Dynamic quick actions triggers
  document.getElementById('qa-register').addEventListener('click', () => {
    document.getElementById('btn-open-register-modal').click();
  });
  document.getElementById('qa-book').addEventListener('click', () => {
    switchView('bookings');
  });
  document.getElementById('qa-maint').addEventListener('click', () => {
    document.getElementById('btn-open-maint-modal').click();
  });

  // Modals Open triggers
  document.getElementById('btn-open-register-modal').addEventListener('click', () => {
    document.getElementById('register-asset-form').reset();
    document.getElementById('reg-date').value = new Date().toISOString().split('T')[0];
    document.getElementById('modal-register-asset').classList.add('active');
  });

  document.getElementById('btn-open-maint-modal').addEventListener('click', () => {
    document.getElementById('raise-maintenance-form').reset();
    document.getElementById('modal-raise-maintenance').classList.add('active');
  });

  // Asset Creation Submission
  document.getElementById('register-asset-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      name: document.getElementById('reg-name').value,
      serial_number: document.getElementById('reg-serial').value,
      category_id: parseInt(document.getElementById('reg-category').value),
      condition: document.getElementById('reg-condition').value,
      location: document.getElementById('reg-location').value,
      acquisition_cost: parseFloat(document.getElementById('reg-cost').value || '0.00'),
      acquisition_date: document.getElementById('reg-date').value,
      is_shared: document.getElementById('reg-shared').checked
    };

    const res = await apiFetch('/api/assets', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res) {
      showToast('Asset Registered', `Created asset ${res.asset_tag} (${res.name})`, 'success');
      closeAllModals();
      loadSupportingData();
      searchAssets();
      loadDashboardData();
    }
  });

  // Return Check-in Submission
  document.getElementById('return-asset-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('return-asset-id-hidden').value;
    const payload = {
      return_condition: document.getElementById('ret-condition').value,
      check_in_notes: document.getElementById('ret-notes').value || ''
    };

    const res = await apiFetch(`/api/allocations/return/${id}`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res) {
      showToast('Asset Returned', `Asset tag ${res.asset_tag} returned to available pool.`, 'success');
      closeAllModals();
      loadSupportingData();
      searchAssets();
      loadDashboardData();
    }
  });

  // Allocation Submission
  document.getElementById('allocate-asset-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('alloc-asset-id').value;
    const empId = document.getElementById('alloc-emp-id').value;
    const deptId = document.getElementById('alloc-dept-id').value;
    const retDate = document.getElementById('alloc-return-date').value;

    const payload = {
      employee_id: empId ? parseInt(empId) : null,
      department_id: deptId ? parseInt(deptId) : null,
      expected_return_date: retDate || null
    };

    const res = await apiFetch(`/api/allocations/allocate/${id}`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    // Conflict error handled by wrapper showing toast, double-allocation warnings
    if (res && !res.error) {
      showToast('Allocated', `Successfully allocated to holder.`, 'success');
      document.getElementById('allocate-asset-form').reset();
      document.getElementById('alloc-asset-id').dispatchEvent(new Event('change'));
      loadSupportingData();
      loadDashboardData();
    }
  });

  // Transfer Request Submission
  document.getElementById('btn-submit-transfer-req').addEventListener('click', async () => {
    const id = document.getElementById('alloc-asset-id').value;
    const toEmpId = document.getElementById('alloc-emp-id').value;
    if (!toEmpId) {
      showToast('Validation Error', 'Must select an employee to request transfer to.', 'warning');
      return;
    }
    const reasonStr = prompt('Enter reason for transfer request:');
    if (!reasonStr) {
      showToast('Canceled', 'Transfer request reason is required.', 'warning');
      return;
    }

    const payload = {
      to_employee_id: parseInt(toEmpId),
      reason: reasonStr
    };

    const res = await apiFetch(`/api/allocations/transfer-request/${id}`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res) {
      showToast('Transfer Requested', 'Transfer request logged in database.', 'success');
      document.getElementById('allocate-asset-form').reset();
      document.getElementById('alloc-asset-id').dispatchEvent(new Event('change'));
      loadSupportingData();
      loadDashboardData();
      loadAllocationsData();
    }
  });

  // Resource Booking Submission
  document.getElementById('book-resource-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      asset_id: parseInt(document.getElementById('book-asset-id').value),
      start_time: new Date(document.getElementById('book-start').value).toISOString(),
      end_time: new Date(document.getElementById('book-end').value).toISOString()
    };

    const res = await apiFetch('/api/bookings', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res) {
      showToast('Resource Booked', 'Booking confirms successfully!', 'success');
      document.getElementById('book-resource-form').reset();
      loadBookingsData();
      loadDashboardData();
    }
  });

  // Maintenance Request Submission
  document.getElementById('raise-maintenance-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      asset_id: parseInt(document.getElementById('maint-asset-id').value),
      priority: document.getElementById('maint-priority').value,
      description: document.getElementById('maint-desc').value,
      photo_url: '' // Optional
    };

    const res = await apiFetch('/api/maintenance', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res) {
      showToast('Ticket Raised', 'Maintenance ticket submitted for review.', 'success');
      closeAllModals();
      loadMaintenanceData();
      loadDashboardData();
    }
  });

  // Maintenance Ticket Management Update (Asset Manager)
  document.getElementById('manage-maintenance-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('manage-maint-id-hidden').value;
    const payload = {
      status: document.getElementById('manage-maint-status').value,
      technician_name: document.getElementById('manage-maint-tech').value || null,
      resolution_notes: document.getElementById('manage-maint-notes').value || null
    };

    const res = await apiFetch(`/api/maintenance/${id}/status`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    });

    if (res) {
      showToast('Success', `Ticket #${id} status updated.`, 'success');
      closeAllModals();
      loadMaintenanceData();
      loadDashboardData();
      loadSupportingData(); // Refreshes asset statuses
    }
  });

  // Admin Tab Controller
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      document.querySelectorAll('.admin-tab-content').forEach(c => c.classList.add('d-none'));
      const activeTabId = btn.dataset.tab;
      document.getElementById(activeTabId).classList.remove('d-none');
    });
  });

  // Admin: Create Department Submission
  document.getElementById('create-dept-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const parentId = document.getElementById('dept-parent-id').value;
    const payload = {
      name: document.getElementById('dept-name').value,
      parent_department_id: parentId ? parseInt(parentId) : null,
      status: 'Active'
    };

    const res = await apiFetch('/api/org/departments', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res) {
      showToast('Department Added', `Created ${res.name}`, 'success');
      document.getElementById('create-dept-form').reset();
      loadDepartmentsTab();
      loadSupportingData();
    }
  });

  // Admin: Create Category Submission
  document.getElementById('create-cat-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      name: document.getElementById('cat-name').value,
      category_specific_fields: [] // Optional JSON
    };

    const res = await apiFetch('/api/org/categories', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res) {
      showToast('Category Added', `Created ${res.name}`, 'success');
      document.getElementById('create-cat-form').reset();
      loadCategoriesTab();
      loadSupportingData();
    }
  });

  // Admin: Promote Employee Submission
  document.getElementById('promote-employee-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('promote-emp-id-hidden').value;
    const deptId = document.getElementById('promote-dept').value;
    const payload = {
      role: document.getElementById('promote-role').value,
      department_id: deptId ? parseInt(deptId) : null,
      status: document.getElementById('promote-status').value
    };

    const res = await apiFetch(`/api/org/employees/${id}/role`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    });

    if (res) {
      showToast('Profile Updated', 'Employee details saved.', 'success');
      closeAllModals();
      loadEmployeesTab();
      loadSupportingData();
    }
  });

  // Admin: Create Audit Cycle Submission
  document.getElementById('create-audit-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const auditorSelect = document.getElementById('audit-auditors');
    const selectedAuditors = Array.from(auditorSelect.selectedOptions).map(opt => parseInt(opt.value));
    
    if (selectedAuditors.length === 0) {
      showToast('Validation Error', 'Must assign at least one auditor.', 'warning');
      return;
    }

    const payload = {
      name: document.getElementById('audit-name').value,
      start_date: document.getElementById('audit-start').value,
      end_date: document.getElementById('audit-end').value,
      scope_type: document.getElementById('audit-scope-type').value,
      scope_value: document.getElementById('audit-scope-value').value || null,
      auditor_ids: selectedAuditors
    };

    const res = await apiFetch('/api/audits/cycles', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res) {
      showToast('Audit Cycle Launched', `Initiated verification audit: ${res.name}`, 'success');
      document.getElementById('create-audit-form').reset();
      loadAuditsData();
    }
  });

  // Notifications Filter change trigger
  document.getElementById('notif-filter').addEventListener('change', loadNotificationsData);

  // Poll notifications count periodically (every 30s)
  setInterval(updateNotificationBadge, 30000);
});
