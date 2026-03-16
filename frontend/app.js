document.addEventListener('DOMContentLoaded', () => {
    // --- State ---
    const state = {
        currentPage: 'dashboard',
        companies: [],
        clients: [],
        currentShippingAddresses: [],
        taxMode: 'CGST+SGST'
    };

    const API_BASE = '/api';

    // --- Address Automation Constants ---
    const gstStateCodes = [
        { id: "1", text: "JAMMU AND KASHMIR" },
        { id: "2", text: "HIMACHAL PRADESH" },
        { id: "3", text: "PUNJAB" },
        { id: "4", text: "CHANDIGARH" },
        { id: "5", text: "UTTARAKHAND" },
        { id: "6", text: "HARYANA" },
        { id: "7", text: "DELHI" },
        { id: "8", text: "RAJASTHAN" },
        { id: "9", text: "UTTAR PRADESH" },
        { id: "10", text: "BIHAR" },
        { id: "11", text: "SIKKIM" },
        { id: "12", text: "ARUNACHAL PRADESH" },
        { id: "13", text: "NAGALAND" },
        { id: "14", text: "MANIPUR" },
        { id: "15", text: "MIZORAM" },
        { id: "16", text: "TRIPURA" },
        { id: "17", text: "MEGHALAYA" },
        { id: "18", text: "ASSAM" },
        { id: "19", text: "WEST BENGAL" },
        { id: "20", text: "JHARKHAND" },
        { id: "21", text: "ODISHA" },
        { id: "22", text: "CHHATTISGARH" },
        { id: "23", text: "MADHYA PRADESH" },
        { id: "24", text: "GUJARAT" },
        { id: "25", text: "DAMAN AND DIU" },
        { id: "26", text: "DADRA AND NAGAR HAVELI" },
        { id: "27", text: "MAHARASHTRA" },
        { id: "29", text: "KARNATAKA" },
        { id: "30", text: "GOA" },
        { id: "31", text: "LAKSHADWEEP" },
        { id: "32", text: "KERALA" },
        { id: "33", text: "TAMIL NADU" },
        { id: "34", text: "PUDUCHERRY" },
        { id: "35", text: "ANDAMAN AND NICOBAR" },
        { id: "36", text: "TELANGANA" },
        { id: "37", text: "ANDHRA PRADESH" },
        { id: "38", text: "LADAKH" },
        { id: "96", text: "OTHER COUNTRIES" },
        { id: "97", text: "Other Territory" }
    ];

    const countries = [
        { id: "India", text: "India" },
        { id: "Other", text: "Other Countries" }
    ];

    // --- Selectors ---
    const pages = document.querySelectorAll('.page');
    const navLinks = document.querySelectorAll('.nav-links li');
    const toast = document.getElementById('toast');

    // --- Routing ---
    function navigateTo(pageId) {
        state.currentPage = pageId;
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        const pageElement = document.getElementById(`${pageId}-page`) || document.getElementById(pageId);
        if (pageElement) pageElement.classList.add('active');
        // Expose globally so inline onclick="navigateTo(...)" in HTML works
        window.navigateTo = navigateTo;

        navLinks.forEach(l => {
            // Find the <a> tag inside this <li>
            const linkTag = l.querySelector('a');
            if (linkTag && linkTag.dataset.page === pageId) {
                // If it's a submenu item, highlight the parent group
                const group = linkTag.closest('.has-submenu') || l;
                document.querySelectorAll('.sidebar li').forEach(li => li.classList.remove('active'));
                group.classList.add('active');
            } else if (l.id === `nav-${pageId}-group`) {
                // For direct top-level items like Dashboard
                document.querySelectorAll('.sidebar li').forEach(li => li.classList.remove('active'));
                l.classList.add('active');
            }
        });

        // Set Header Text
        const titleMap = {
            'dashboard': ['Dashboard', 'Overview of your invoicing activity.'],
            'invoice-entry': ['New Invoice', 'Single-page entry for professional billing.'],
            'invoice-new': ['New GST Invoice', 'Fill all details and generate a professional invoice.'],
            'invoice-list': ['Invoice History', 'View and download all saved invoices.'],
            'clients-list': ['Clients List', 'View all registered clients.'],
            'client-add': ['Add Client', 'Register a new buyer or client.'],
            'client-update': ['Update / Delete Client', 'Modify or remove an existing client.'],
            'shipping-list': ['Shipping Addresses', 'All shipping addresses linked to clients.'],
            'shipping-add': ['Add Shipping Address', 'Assign a new shipping address to a client.'],
            'shipping-update': ['Update / Delete Shipping', 'Modify or remove a shipping address.'],
            'profile-list': ['Companies List', 'Manage your business identities.'],
            'profile-add': ['Add Company', 'Create a new business profile.'],
            'profile-update': ['Update Company', 'Modify existing business details.'],
            'reports': ['Reports & Analytics', 'Filter by Financial Year to view reports.'],
            'settings': ['Settings & Data', 'Manage your database and backups.']
        };
        const [t, s] = titleMap[pageId] || ['', ''];
        document.getElementById('page-title').innerText = t;
        document.getElementById('page-subtitle').innerText = s;

        if (pageId === 'dashboard') loadDashboard();
        if (pageId === 'reports') openReportsPage();
        if (pageId === 'invoice-entry') resetEntryForm();
        if (pageId === 'invoice-new') openNewInvoice();
        if (pageId === 'invoice-list') loadInvoiceList();
        if (pageId === 'profile-list') loadCompanyList();
        if (pageId === 'profile-add') openAddCompany();
        if (pageId === 'profile-update') openUpdateCompany();
        if (pageId === 'clients-list') loadClientList();
        if (pageId === 'client-add') openAddClient();
        if (pageId === 'client-update') openUpdateClient();
        if (pageId === 'shipping-list') loadShippingList();
        if (pageId === 'shipping-add') openAddShipping();
        if (pageId === 'shipping-update') openUpdateShipping();
    }

    // Load business identity in sidebar and set favicon
    async function initBusinessIdentity() {
        try {
            const res = await fetch(`${API_BASE}/profiles`);
            const companies = await res.json();
            const nameEl = document.getElementById('owner-name');
            if (companies.length === 0) {
                nameEl.innerText = 'Set Up Profile';
                updateFavicon(null); // default
            } else {
                const def = companies.find(c => c.is_default) || companies[0];
                nameEl.innerText = def.name;
                updateFavicon(def.favicon_url);

                // Update sidebar logo if available
                const header = document.querySelector('.sidebar-header');
                if (header && def.favicon_url) {
                    let logo = header.querySelector('.logo-image') || header.querySelector('.logo-icon');
                    if (logo) {
                        const img = document.createElement('img');
                        img.src = def.favicon_url;
                        img.className = 'logo-image';
                        img.style = 'width: 32px; height: 32px; object-fit: contain; margin-right: 12px; border-radius: 6px; background: white; padding: 2px;';
                        logo.replaceWith(img);
                    }
                }
            }
        } catch (e) {
            console.error("Identity init failed", e);
            document.getElementById('owner-name').innerText = 'Invoice System';
            updateFavicon(null);
        }
    }
    initBusinessIdentity();

    function updateFavicon(url) {
        let link = document.querySelector("link[rel~='icon']");
        if (!link) {
            link = document.createElement('link');
            link.rel = 'icon';
            document.getElementsByTagName('head')[0].appendChild(link);
        }
        // If url is null/empty, it will default to favicon.ico (which might 404 but we can't do much if no logo uploaded)
        // However, we can try to avoid the 404 log if we know it's missing by using a placeholder or just letting it be.
        link.href = url || 'favicon.ico';
    }

    async function handleFaviconUpload(profileId, file, form) {
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        try {
            console.log(`Uploading favicon for ${profileId}...`);
            const res = await fetch(`${API_BASE}/profiles/${profileId}/favicon`, {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                const result = await res.json();
                console.log("Favicon uploaded successfully:", result.favicon_url);
                
                // Update hidden field
                $(form).find('.favicon-url-hidden').val(result.favicon_url);
                
                const isDefault = $(form).find('[name="is_default"]').prop('checked') || state.companies.length <= 1;
                if (isDefault) updateFavicon(result.favicon_url);
            } else {
                console.error("Favicon upload failed status:", res.status);
            }
        } catch (e) { console.error("Favicon upload error", e); }
    }

    // Toggle submenus
    document.querySelectorAll('.has-submenu > a').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const parent = link.parentElement;
            parent.classList.toggle('open');
            // Navigate to main submenu page
            navigateTo(link.dataset.page);
        });
    });

    // Handle all page links
    document.querySelectorAll('[data-page]').forEach(l => {
        if (!l.classList.contains('nav-link') || !l.parentElement.classList.contains('has-submenu')) {
            l.addEventListener('click', (e) => {
                e.preventDefault();
                navigateTo(l.dataset.page);
            });
        }
    });

    document.getElementById('btn-create-invoice').addEventListener('click', () => navigateTo('invoice-entry'));

    // --- Feedback ---
    let toastCallback = null;

    function showToast(msg, type = 'success', callback = null) {
        toastCallback = callback;
        const modal = document.getElementById('message-modal');
        const text = document.getElementById('message-text');
        const iconDiv = document.getElementById('message-icon');
        const title = document.getElementById('message-title');

        if (!modal || !text) {
            console.error("Notification modal or text element missing!");
            alert(msg); // Fallback to alert if modal structure is broken
            return;
        }

        text.innerText = msg;
        
        // Customize based on type
        if (iconDiv && title) {
            if (type === 'error') {
                iconDiv.innerHTML = '<i class="fas fa-exclamation-circle" style="color: #ef4444;"></i>';
                title.innerText = 'Error';
            } else if (type === 'info') {
                iconDiv.innerHTML = '<i class="fas fa-info-circle" style="color: #3b82f6;"></i>';
                title.innerText = 'Information';
            } else {
                iconDiv.innerHTML = '<i class="fas fa-check-circle" style="color: #10b981;"></i>';
                title.innerText = 'Success';
            }
        }

        modal.classList.add('active');
    }
    window.showToast = showToast;

    window.closeMessageModal = function() {
        document.getElementById('message-modal').classList.remove('active');
        if (typeof toastCallback === 'function') {
            const cb = toastCallback;
            toastCallback = null; // Clear before calling to avoid loops
            cb();
        }
    };

    // --- Profile & Business Branding ---
    function initAddressAutomation(formId) {
        const countrySelect = $(`#${formId} .profile-country`);
        const stateSelect = $(`#${formId} .profile-state`);
        const citySelect = $(`#${formId} .profile-city`);
        const pincodeInput = $(`#${formId} .profile-pincode`);
        const stateCodeInput = $(`#${formId} .profile-state-code`);
        const statusMsg = $(`#${formId}`).find('.status-msg').length ? $(`#${formId}`).find('.status-msg') : { text: function() {} };

        countrySelect.select2({ data: countries, placeholder: "Select Country", allowClear: true });
        stateSelect.select2({ placeholder: "Select State", allowClear: true });
        citySelect.select2({ placeholder: "Select City", allowClear: true, tags: true });

        countrySelect.on('change', function () {
            const val = $(this).val();
            stateSelect.empty().append('<option></option>');
            citySelect.empty().append('<option></option>').prop('disabled', true);
            if (val === "India") {
                stateSelect.select2({ data: gstStateCodes }).prop('disabled', false);
            } else if (val) {
                stateSelect.select2({ data: [{ id: "96", text: "OTHER COUNTRIES" }] }).prop('disabled', false).val("96").trigger('change');
            }
        });

        stateSelect.on('change', function () {
            const stateName = $(this).find(':selected').text();
            const stateCode = $(this).val();
            stateCodeInput.val(stateCode);
            citySelect.empty().append('<option></option>');

            if (!stateName || stateName === "OTHER COUNTRIES") {
                if (stateName) citySelect.prop('disabled', false);
                return;
            }

            statusMsg.text(`Fetching cities for ${stateName}...`);
            $.ajax({
                url: 'https://countriesnow.space/api/v0.1/countries/state/cities',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ country: "India", state: stateName }),
                success: function (res) {
                    statusMsg.text("");
                    if (res && res.data && res.data.length > 0) {
                        const cityData = res.data.map(c => ({ id: c, text: c }));
                        citySelect.select2({ data: cityData, tags: true, placeholder: 'Select or type city...', allowClear: true }).prop('disabled', false);
                    } else {
                        citySelect.select2({ tags: true, placeholder: 'Type city name...', allowClear: true }).prop('disabled', false);
                    }
                },
                error: function () {
                    statusMsg.text("");
                    citySelect.select2({ tags: true, placeholder: 'Type city name...', allowClear: true }).prop('disabled', false);
                }
            });
        });

        citySelect.on('change', function () {
            const city = $(this).val();
            if (!city || countrySelect.val() !== "India") return;
            // Silently try to pre-fill pincode; if city doesn't match a post office name, user types it manually
            fetch('https://api.postalpincode.in/postoffice/' + encodeURIComponent(city))
                .then(r => r.ok ? r.json() : null)
                .then(res => {
                    if (res && res[0] && res[0].Status === "Success" && res[0].PostOffice.length > 0) {
                        pincodeInput.val(res[0].PostOffice[0].Pincode);
                    }
                })
                .catch(() => { }); // silently ignore — user can type pincode manually
        });
    }

    // --- Multi-Company Management ---
    async function loadCompanyList() {
        try {
            const res = await fetch(`${API_BASE}/profiles`);
            state.companies = await res.json();

            const tbody = document.querySelector('#companies-table tbody');
            tbody.innerHTML = '';

            if (state.companies.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">No companies added yet.</td></tr>';
                document.getElementById('owner-name').innerText = "Set Up Profile";
                return;
            }

            const defaultComp = state.companies.find(c => c.is_default) || state.companies[0];
            document.getElementById('owner-name').innerText = defaultComp.name;

            state.companies.forEach((comp, idx) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${idx + 1}</td>
                    <td>${comp.name}</td>
                    <td>${comp.address_line_1}</td>
                    <td>${comp.city || 'N/A'}</td>
                    <td>${comp.state_name || 'N/A'}</td>
                    <td>${comp.gstin || 'N/A'}</td>
                    <td>
                        <input type="radio" name="default_company" value="${comp.id}" ${comp.is_default ? 'checked' : ''} onchange="window.setDefaultCompany('${comp.id}')">
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) { console.error("Failed to load companies", e); }
    }

    window.setDefaultCompany = async function (id) {
        try {
            await fetch(`${API_BASE}/profiles/${id}/default`, { method: 'PUT' });
            showToast("Default company updated");
            loadCompanyList();
        } catch (e) {
            console.error(e);
            showToast("Failed to set default", "error");
        }
    };

    function setupProfileForm(containerId) {
        const container = document.getElementById(containerId);
        if (container.innerHTML.trim() === '') {
            container.innerHTML = document.getElementById('profile-form-template').innerHTML;
            initAddressAutomation(container.closest('form').getAttribute('id'));
            
            // Preview logic for favicon
            const form = container.closest('form');
            const fileInput = form.querySelector('.profile-favicon-input');
            const preview = form.querySelector('.favicon-preview img') || form.querySelector('.favicon-preview');
            
            fileInput.addEventListener('change', function() {
                const file = this.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        if (preview.tagName === 'IMG') {
                            preview.src = e.target.result;
                        } else {
                            preview.innerHTML = `<img src="${e.target.result}" style="width:100%; height:100%; object-fit:contain;">`;
                        }
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    }

    function openAddCompany() {
        setupProfileForm('profile-add-fields');
        document.getElementById('profile-add-form').reset();
        $('#profile-add-form .profile-country').val(null).trigger('change');
    }

    async function openUpdateCompany() {
        const select = document.getElementById('company-select');
        select.innerHTML = '<option value="">-- Select Company --</option>' +
            state.companies.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        document.getElementById('profile-update-form').style.display = 'none';

        select.onchange = async (e) => {
            const id = e.target.value;
            if (!id) {
                document.getElementById('profile-update-form').style.display = 'none';
                return;
            }
            setupProfileForm('profile-update-fields');
            document.getElementById('profile-update-form').style.display = 'block';

            try {
                const res = await fetch(`${API_BASE}/profiles/${id}`);
                const data = await res.json();

                const form = document.getElementById('profile-update-form');
                document.getElementById('update-company-id').value = id;

                Object.keys(data).forEach(k => {
                    const el = form.querySelector(`[name="${k}"]`);
                    if (el && el.tagName !== 'SELECT') el.value = data[k] || '';
                });

                if (data.country) $(form).find('.profile-country').val(data.country).trigger('change');
                if (data.state_name) {
                    setTimeout(() => {
                        $(form).find('.profile-state').val(data.state_code).trigger('change');
                        if (data.city) {
                            setTimeout(() => {
                                const citySelect = $(form).find('.profile-city');
                                if (!citySelect.find(`option[value="${data.city}"]`).length) {
                                    const newOption = new Option(data.city, data.city, true, true);
                                    citySelect.append(newOption).trigger('change');
                                } else {
                                    citySelect.val(data.city).trigger('change');
                                }
                            }, 800);
                        }
                    }, 500);
                }
                
                // Populate hidden favicon URL
                $(form).find('.favicon-url-hidden').val(data.favicon_url || '');

                if (data.favicon_url) {
                    const preview = form.querySelector('.favicon-preview');
                    preview.innerHTML = `<img src="${data.favicon_url}" style="width:100%; height:100%; object-fit:contain;">`;
                    const pathText = form.querySelector('.favicon-path-text');
                    if (pathText) pathText.textContent = `Current: ${data.favicon_url.split('/').pop()}`;
                } else {
                    const preview = form.querySelector('.favicon-preview');
                    preview.innerHTML = `<i class="fas fa-image" style="color:#ccc;"></i>`;
                }

            } catch (e) { console.error(e); showToast("Failed to load company", "error"); }
        };
    }

    document.getElementById('profile-add-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData);
        data.state_name = $(e.target).find('.profile-state').find(':selected').text();
        // is_default is managed by the backend; remove it to avoid a 422 type error
        delete data.is_default;

        try {
            const res = await fetch(`${API_BASE}/profiles`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                const result = await res.json();
                const fileInput = e.target.querySelector('.profile-favicon-input');
                if (fileInput && fileInput.files[0]) {
                    await handleFaviconUpload(result.id, fileInput.files[0], e.target);
                }
                showToast("Company Added!");
                initBusinessIdentity(); // Update sidebar/favicon
                navigateTo('profile-list');
                document.getElementById('profile-add-form').reset();
            }
        } catch (e) { showToast("Error adding company", "error"); }
    });

    document.getElementById('profile-update-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('update-company-id').value;
        const fileInput = e.target.querySelector('.profile-favicon-input');
        
        try {
            // 1. If a new logo is selected, upload it FIRST
            if (fileInput && fileInput.files[0]) {
                console.log("New logo detected, uploading first...");
                await handleFaviconUpload(id, fileInput.files[0], e.target);
            }

            // 2. Now perform the profile update (the hidden field should have been updated by handleFaviconUpload)
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            data.state_name = $(e.target).find('.profile-state').find(':selected').text();

            const res = await fetch(`${API_BASE}/profiles/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (res.ok) {
                console.log("Profile details updated successfully");
                showToast("Company Profile Updated!");
                initBusinessIdentity(); 
                navigateTo('profile-list');
            } else {
                const errorData = await res.json();
                console.error("Profile update failed:", errorData);
                showToast('Update failed: ' + (errorData.detail || res.statusText), 'error');
            }
        } catch (err) {
            showToast("Network error updating profile", "error");
        }
    });

    document.getElementById('btn-delete-company').addEventListener('click', async () => {
        if (!confirm("Are you sure you want to delete this company?")) return;
        const id = document.getElementById('update-company-id').value;
        try {
            const res = await fetch(`${API_BASE}/profiles/${id}`, { method: 'DELETE' });
            if (res.ok) {
                showToast("Company Deleted!");
                navigateTo('profile-list');
            }
        } catch (e) { showToast("Error deleting company", "error"); }
    });

    // Initial Load is handled at the bottom of the script

    // =============================================
    // CLIENTS DIRECTORY MODULE
    // =============================================

    async function loadClientList() {
        const tbody = document.querySelector('#clients-table tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        try {
            const res = await fetch(`${API_BASE}/clients`);
            state.clients = await res.json();
            if (state.clients.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center">No clients added yet.</td></tr>';
                return;
            }
            state.clients.forEach((c, idx) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${idx + 1}</td><td>${c.name}</td><td>${c.billing_address_line_1 || ''}</td><td>${c.city || 'N/A'}</td><td>${c.state_name || 'N/A'}</td><td>${c.gstin || 'N/A'}</td>`;
                tbody.appendChild(tr);
            });
        } catch (e) { console.error('Failed to load clients', e); }
    }

    function setupClientForm(containerId) {
        const container = document.getElementById(containerId);
        if (container && container.innerHTML.trim() === '') {
            container.innerHTML = document.getElementById('client-form-template').innerHTML;
            initAddressAutomation(container.closest('form').getAttribute('id'));
        }
    }

    function openAddClient() {
        setupClientForm('client-add-fields');
        document.getElementById('client-add-form').reset();
        $('#client-add-form .profile-country').val(null).trigger('change');
    }

    async function openUpdateClient() {
        // Always fetch fresh so newly added clients appear immediately
        const res = await fetch(`${API_BASE}/clients`);
        state.clients = await res.json();

        const select = document.getElementById('client-select');
        select.innerHTML = '<option value="">-- Select Client --</option>' +
            state.clients.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        $(select).select2({ placeholder: '-- Select Client --', allowClear: true, width: '100%' });
        document.getElementById('client-update-form').style.display = 'none';

        $(select).off('change').on('change', async function () {
            const id = this.value;
            if (!id) { document.getElementById('client-update-form').style.display = 'none'; return; }
            setupClientForm('client-update-fields');
            document.getElementById('client-update-form').style.display = 'block';
            document.getElementById('update-client-id').value = id;
            try {
                const res = await fetch(`${API_BASE}/clients/${id}`);
                const data = await res.json();
                const form = document.getElementById('client-update-form');
                Object.keys(data).forEach(k => {
                    const el = form.querySelector(`[name="${k}"]`);
                    if (el && el.tagName !== 'SELECT') el.value = data[k] || '';
                });
                if (data.country) $(form).find('.profile-country').val(data.country).trigger('change');
                if (data.state_name) {
                    setTimeout(() => $(form).find('.profile-state').val(data.state_code).trigger('change'), 500);
                    if (data.city) setTimeout(() => {
                        const cs = $(form).find('.profile-city');
                        if (!cs.find(`option[value="${data.city}"]`).length) cs.append(new Option(data.city, data.city, true, true)).trigger('change');
                        else cs.val(data.city).trigger('change');
                    }, 900);
                }
            } catch (e) { showToast('Failed to load client', 'error'); }
        });
    }

    async function loadClientListForSelect() {
        if (!state.clients || state.clients.length === 0) {
            const res = await fetch(`${API_BASE}/clients`);
            state.clients = await res.json();
        }
    }

    document.getElementById('client-add-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target));
        data.state_name = $(e.target).find('.profile-state').find(':selected').text();
        try {
            const res = await fetch(`${API_BASE}/clients`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            if (res.ok) { showToast('Client Added!'); state.clients = []; navigateTo('clients-list'); e.target.reset(); }
            else { const err = await res.json(); showToast(err.detail || 'Error', 'error'); }
        } catch (e) { showToast('Error adding client', 'error'); }
    });

    document.getElementById('client-update-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('update-client-id').value;
        const data = Object.fromEntries(new FormData(e.target));
        data.state_name = $(e.target).find('.profile-state').find(':selected').text();
        try {
            const res = await fetch(`${API_BASE}/clients/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                showToast('Client Updated!');
                state.clients = [];
                navigateTo('clients-list');
            } else {
                const errorData = await res.json();
                showToast('Update failed: ' + (errorData.detail || res.statusText), 'error');
            }
        } catch (err) {
            showToast('Network error updating client', 'error');
        }
    });

    document.getElementById('btn-delete-client').addEventListener('click', async () => {
        if (!confirm('Delete this client and all their shipping addresses?')) return;
        const id = document.getElementById('update-client-id').value;
        try {
            const res = await fetch(`${API_BASE}/clients/${id}`, { method: 'DELETE' });
            if (res.ok) { showToast('Client Deleted!'); state.clients = []; navigateTo('clients-list'); }
        } catch (e) { showToast('Error deleting client', 'error'); }
    });

    // =============================================
    // SHIPPING ADDRESSES MODULE
    // =============================================

    async function loadShippingList() {
        const tbody = document.querySelector('#shipping-table tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        try {
            const res = await fetch(`${API_BASE}/shipping`);
            const rows = await res.json();
            if (rows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">No shipping addresses added yet.</td></tr>';
                return;
            }
            rows.forEach((s, idx) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${idx + 1}</td><td>${s.client_name}</td><td>${s.branch_name || 'N/A'}</td><td>${s.address_line_1 || ''}</td><td>${s.city || 'N/A'}</td><td>${s.state_name || 'N/A'}</td><td>${s.gstin || 'N/A'}</td>`;
                tbody.appendChild(tr);
            });
        } catch (e) { console.error('Failed to load shipping', e); }
    }

    function setupShippingForm(containerId) {
        const container = document.getElementById(containerId);
        if (container && container.innerHTML.trim() === '') {
            container.innerHTML = document.getElementById('shipping-form-template').innerHTML;
            initAddressAutomation(container.closest('form').getAttribute('id'));
        }
    }

    async function openAddShipping() {
        const res = await fetch(`${API_BASE}/clients`);
        state.clients = await res.json();
        const sel = document.getElementById('shipping-client-select-add');
        if (sel) {
            sel.innerHTML = '<option value="">-- Select Client --</option>' + state.clients.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
            $(sel).select2({ placeholder: '-- Select Client --', allowClear: true, width: '100%' });
        }
        setupShippingForm('shipping-add-fields');
        document.getElementById('shipping-add-form').reset();
        $('#shipping-add-form .profile-country').val(null).trigger('change');
    }

    async function openUpdateShipping() {
        const res = await fetch(`${API_BASE}/clients`);
        state.clients = await res.json();

        const clientSel = document.getElementById('shipping-client-select-update');
        const shipSel = document.getElementById('shipping-address-select');

        // Destroy any previous Select2 instances to start clean
        if ($(clientSel).hasClass('select2-hidden-accessible')) $(clientSel).select2('destroy');
        if ($(shipSel).hasClass('select2-hidden-accessible')) $(shipSel).select2('destroy');

        // Populate and initialise client dropdown
        clientSel.innerHTML = '<option value="">-- Select Client --</option>' +
            state.clients.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        $(clientSel).select2({ placeholder: '-- Select Client --', allowClear: true, width: '100%' });

        // Initialise empty shipping-address dropdown
        shipSel.innerHTML = '<option value="">-- Select Shipping Address --</option>';
        $(shipSel).select2({ placeholder: '-- Select Shipping Address --', allowClear: true, width: '100%' });

        document.getElementById('shipping-update-form').style.display = 'none';

        function attachShipSelHandler() {
            $(shipSel).off('change.shipupdate').on('change.shipupdate', async function () {
                const sid = this.value;
                if (!sid) { document.getElementById('shipping-update-form').style.display = 'none'; return; }
                setupShippingForm('shipping-update-fields');
                document.getElementById('shipping-update-form').style.display = 'block';
                document.getElementById('update-shipping-id').value = sid;
                try {
                    const r = await fetch(`${API_BASE}/shipping/${sid}`);
                    const data = await r.json();
                    const form = document.getElementById('shipping-update-form');
                    Object.keys(data).forEach(k => {
                        const el = form.querySelector(`[name="${k}"]`);
                        if (el && el.tagName !== 'SELECT') el.value = data[k] || '';
                    });
                    if (data.country) $(form).find('.profile-country').val(data.country).trigger('change');
                    if (data.state_name) {
                        setTimeout(() => $(form).find('.profile-state').val(data.state_code).trigger('change'), 500);
                        if (data.city) setTimeout(() => {
                            const cs = $(form).find('.profile-city');
                            if (!cs.find(`option[value="${data.city}"]`).length)
                                cs.append(new Option(data.city, data.city, true, true)).trigger('change');
                            else cs.val(data.city).trigger('change');
                        }, 900);
                    }
                } catch (e) { showToast('Failed to load shipping address', 'error'); }
            });
        }
        attachShipSelHandler();

        // Use select2:select so it only fires on explicit user selection (not on programmatic changes)
        $(clientSel).off('select2:select select2:unselect').on('select2:select', async function (e) {
            const clientId = e.params.data.id;
            document.getElementById('shipping-update-form').style.display = 'none';

            // Destroy → clear → re-init shipSel so no events bleed into clientSel
            if ($(shipSel).hasClass('select2-hidden-accessible')) $(shipSel).select2('destroy');
            shipSel.innerHTML = '<option value="">-- Select Shipping Address --</option>';
            $(shipSel).select2({ placeholder: '-- Select Shipping Address --', allowClear: true, width: '100%' });

            const r = await fetch(`${API_BASE}/clients/${clientId}/shipping`);
            const addresses = await r.json();
            addresses.forEach(s => shipSel.appendChild(new Option(s.branch_name || s.address_line_1, s.id)));

            attachShipSelHandler();
        }).on('select2:unselect', function () {
            if ($(shipSel).hasClass('select2-hidden-accessible')) $(shipSel).select2('destroy');
            shipSel.innerHTML = '<option value="">-- Select Shipping Address --</option>';
            $(shipSel).select2({ placeholder: '-- Select Shipping Address --', allowClear: true, width: '100%' });
            document.getElementById('shipping-update-form').style.display = 'none';
            attachShipSelHandler();
        });
    }

    document.getElementById('shipping-add-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target));
        data.state_name = $(e.target).find('.profile-state').find(':selected').text();
        const clientId = document.getElementById('shipping-client-select-add').value;
        if (!clientId) { showToast('Please select a client', 'error'); return; }
        data.client_id = clientId;
        try {
            const res = await fetch(`${API_BASE}/shipping`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            if (res.ok) { showToast('Shipping Address Added!'); navigateTo('shipping-list'); }
            else { const err = await res.json(); showToast(err.detail || 'Error', 'error'); }
        } catch (e) { showToast('Error adding shipping', 'error'); }
    });

    document.getElementById('shipping-update-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('update-shipping-id').value;
        const data = Object.fromEntries(new FormData(e.target));
        data.state_name = $(e.target).find('.profile-state').find(':selected').text();
        data.client_id = document.getElementById('shipping-client-select-update').value;
        try {
            const res = await fetch(`${API_BASE}/shipping/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            if (res.ok) { showToast('Shipping Updated!'); navigateTo('shipping-list'); }
            else { const err = await res.json(); showToast(err.detail || 'Error', 'error'); }
        } catch (e) { showToast('Error updating shipping', 'error'); }
    });

    document.getElementById('btn-delete-shipping').addEventListener('click', async () => {
        if (!confirm('Delete this shipping address?')) return;
        const id = document.getElementById('update-shipping-id').value;
        try {
            const res = await fetch(`${API_BASE}/shipping/${id}`, { method: 'DELETE' });
            if (res.ok) { showToast('Shipping Deleted!'); navigateTo('shipping-list'); }
        } catch (e) { showToast('Error deleting shipping', 'error'); }
    });

    // =============================================
    // (Legacy Invoice Entry Module removed)
    // =============================================


    async function loadDashboard() {
        // Always load Analytics first so it doesn't depend on the table existing
        loadDashboardAnalytics();

        const tbody = document.querySelector('#recent-invoices-table tbody');
        if (!tbody) return;

        try {
            const res = await fetch(`${API_BASE}/invoices`);
            const invoices = await res.json();
            tbody.innerHTML = '';

            let count = invoices.length;
            let amount = 0;

            invoices.forEach(i => {
                amount += i.grand_total;
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${i.invoice_no}</strong></td>
                    <td>${i.invoice_date}</td>
                    <td>${i.client_name}</td>
                    <td class="right" style="white-space: nowrap;">&#8377;&nbsp;${parseFloat(i.total_taxable_value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td class="right" style="white-space: nowrap;">&#8377;&nbsp;${parseFloat(i.total_tax_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td class="right" style="white-space: nowrap;">&#8377;&nbsp;${parseFloat(i.grand_total).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td>
                        <button class="btn btn-link" onclick="window.open('/api/invoices/${i.id}/pdf')"><i class="fas fa-file-pdf"></i> PDF</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            const stc = document.getElementById('stat-total-count');
            if (stc) stc.innerText = count;
            const sta = document.getElementById('stat-total-amount');
            if (sta) sta.innerText = `₹ ${amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        } catch (e) { console.error("Dashboard load failed", e); }
    }

    // ==============================================================
    //  DASHBOARD ANALYTICS (FY Summaries)
    // ==============================================================
    let dashboardSummaryData = [];

    async function loadDashboardAnalytics() {
        try {
            const res = await fetch(`${API_BASE}/dashboard/summary`);
            dashboardSummaryData = await res.json();

            const fyFilter = document.getElementById('fy-filter');
            if (!fyFilter) return;

            // Only populate options if it's currently empty/loading
            if (fyFilter.options.length <= 1) {
                fyFilter.innerHTML = '';
                if (dashboardSummaryData.length === 0) {
                    fyFilter.innerHTML = '<option value="">No Data</option>';
                    return;
                }

                // Sort FYs descending (newest first)
                dashboardSummaryData.sort((a, b) => b.financial_year.localeCompare(a.financial_year));

                dashboardSummaryData.forEach(fy => {
                    const opt = document.createElement('option');
                    opt.value = fy.financial_year;
                    opt.textContent = `FY ${fy.financial_year}`;
                    fyFilter.appendChild(opt);
                });
            }

            // Update KPI cards based on selected FY
            const selectedFy = fyFilter.value;
            const fyData = dashboardSummaryData.find(d => d.financial_year === selectedFy);

            if (fyData) {
                document.getElementById('kpi-total-revenue').innerText = `₹ ${parseFloat(fyData.total_revenue).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                document.getElementById('kpi-invoice-count').innerText = `${fyData.invoice_count} invoices generated`;

                document.getElementById('kpi-bills-receivable').innerText = `₹ ${parseFloat(fyData.bills_receivable).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                document.getElementById('kpi-amount-received').innerText = `₹ ${parseFloat(fyData.total_received).toLocaleString('en-IN', { minimumFractionDigits: 2 })} collected so far`;
            }

            // Also render the charts for this FY
            renderDashboardCharts(selectedFy);

        } catch (e) { console.error("Analytics load failed: ", e); }
    }

    // Expose exclusively so the HTML onchange can call it
    window.loadDashboardAnalytics = loadDashboardAnalytics;

    let revenueChart, clientsChart, hsnChart;

    async function renderDashboardCharts(fy) {
        if (!fy) return;
        try {
            const res = await fetch(`${API_BASE}/dashboard/charts?fy=${fy}`);
            if (!res.ok) throw new Error('Failed to fetch chart data');
            const data = await res.json();

            const chartOptions = { responsive: true, maintainAspectRatio: false, animation: false };

            // 1. Revenue Trend (Line Chart)
            const ctxRev = document.getElementById('chart-revenue-trend');
            if (ctxRev) {
                if (revenueChart) revenueChart.destroy();
                revenueChart = new Chart(ctxRev, {
                    type: 'line',
                    data: {
                        labels: data.monthly_trend.labels,
                        datasets: [{
                            label: 'Revenue (₹)',
                            data: data.monthly_trend.data,
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            fill: true,
                            tension: 0.3
                        }]
                    },
                    options: chartOptions
                });
            }

            // (Removed Pie/Bar Charts for Dashboard - moved to Reports page)

        } catch (e) { console.error("Charts load failed: ", e); }
    }


    // ==============================================================
    //  REPORTS PAGE MODULE
    // ==============================================================
    let reportChartInstance;

    async function openReportsPage() {
        // Fetch dashboard summary just to get FY list (if not cached)
        if (dashboardSummaryData.length === 0) {
            try {
                const res = await fetch(`${API_BASE}/dashboard/summary`);
                dashboardSummaryData = await res.json();
            } catch (e) { console.error("Failed to load FY list", e); return; }
        }

        const fyFilter = document.getElementById('reports-fy-filter');
        if (fyFilter && fyFilter.options.length <= 1) {
            fyFilter.innerHTML = '';
            if (dashboardSummaryData.length === 0) {
                fyFilter.innerHTML = '<option value="">No Data</option>';
            } else {
                dashboardSummaryData.sort((a, b) => b.financial_year.localeCompare(a.financial_year));
                dashboardSummaryData.forEach(fy => {
                    const opt = document.createElement('option');
                    opt.value = fy.financial_year;
                    opt.textContent = `FY ${fy.financial_year}`;
                    fyFilter.appendChild(opt);
                });
            }
        }

        loadSelectedReport();
    }

    async function loadSelectedReport() {
        const fy = document.getElementById('reports-fy-filter').value;
        const type = document.getElementById('report-type-filter').value;
        const container = document.getElementById('report-container');

        if (!fy) {
            container.innerHTML = '<p style="text-align:center; color:#888;">No Financial Year found.</p>';
            return;
        }

        container.innerHTML = '<p style="text-align:center; color:#888;"><i class="fas fa-spinner fa-spin"></i> Generating report...</p>';

        try {
            const res = await fetch(`${API_BASE}/dashboard/charts?fy=${fy}`);
            const data = await res.json();

            // Clean up old chart instance if switching between views
            if (reportChartInstance) reportChartInstance.destroy();
            container.innerHTML = ''; // clear loading text

            if (type === 'monthly_trend') {
                container.innerHTML = `
                    <div style="position: relative; height: 400px; width: 100%;">
                        <canvas id="reports-canvas"></canvas>
                    </div>
                `;
                const ctx = document.getElementById('reports-canvas');
                reportChartInstance = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.monthly_trend.labels,
                        datasets: [{
                            label: 'Monthly Revenue (₹)',
                            data: data.monthly_trend.data,
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            fill: true,
                            tension: 0.3
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false, animation: false }
                });
            }
            else if (type === 'top_clients') {
                const tableStyle = 'width:100%; border-collapse: collapse; font-size: 0.95rem;';
                const thStyle = 'padding: 12px 16px; background:#f4f6f9; color:#555; font-weight:600; border-bottom: 2px solid #ddd; text-align:left;';
                const tdStyle = 'padding: 11px 16px; border-bottom: 1px solid #eee;';
                let html = `
                <table style="${tableStyle}">
                    <thead><tr>
                        <th style="${thStyle} width:60px;">#</th>
                        <th style="${thStyle}">Client Name</th>
                        <th style="${thStyle} text-align:right;">Total Revenue (₹)</th>
                    </tr></thead>
                    <tbody>
                `;
                if (!data.top_clients.labels.length) html += `<tr><td colspan="3" style="text-align:center; padding:20px; color:#999;">No data found for this period.</td></tr>`;
                data.top_clients.labels.forEach((clientName, i) => {
                    const bg = i % 2 === 0 ? 'white' : '#fafbfd';
                    html += `<tr style="background:${bg};">
                        <td style="${tdStyle} color:#888;">${i + 1}</td>
                        <td style="${tdStyle} font-weight:600; color:#333;">${clientName}</td>
                        <td style="${tdStyle} text-align:right; font-family:monospace; color:#1a6e2f;">₹ ${parseFloat(data.top_clients.data[i]).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    </tr>`;
                });
                html += '</tbody></table>';
                container.innerHTML = html;
            }
            else if (type === 'top_products') {
                const tableStyle2 = 'width:100%; border-collapse: collapse; font-size: 0.95rem;';
                const thStyle2 = 'padding: 12px 16px; background:#f4f6f9; color:#555; font-weight:600; border-bottom: 2px solid #ddd; text-align:left;';
                const tdStyle2 = 'padding: 11px 16px; border-bottom: 1px solid #eee;';
                let html2 = `
                <table style="${tableStyle2}">
                    <thead><tr>
                        <th style="${thStyle2} width:60px;">#</th>
                        <th style="${thStyle2}">Product / Service Description</th>
                        <th style="${thStyle2} text-align:right;">Total Sales (₹)</th>
                    </tr></thead>
                    <tbody>
                `;
                if (!data.top_products.labels.length) html2 += `<tr><td colspan="3" style="text-align:center; padding:20px; color:#999;">No data found for this period.</td></tr>`;
                data.top_products.labels.forEach((productName, i) => {
                    const bg2 = i % 2 === 0 ? 'white' : '#fafbfd';
                    html2 += `<tr style="background:${bg2};">
                        <td style="${tdStyle2} color:#888;">${i + 1}</td>
                        <td style="${tdStyle2} font-weight:600; color:#333;">${productName}</td>
                        <td style="${tdStyle2} text-align:right; font-family:monospace; color:#1a6e2f;">₹ ${parseFloat(data.top_products.data[i]).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    </tr>`;
                });
                html2 += '</tbody></table>';
                container.innerHTML = html2;
            }

        } catch (e) {
            console.error(e);
            container.innerHTML = '<p style="text-align:center; color:#e53935;">Error generating report.</p>';
        }
    }

    window.loadSelectedReport = loadSelectedReport;


    // ==============================================================
    //  INVOICE MODULE  (injected & Receipts)
    // ==============================================================

    function getFinancialYear(dateStr) {
        if (!dateStr) return null;
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return null;
        const year = d.getFullYear();
        const month = d.getMonth() + 1; // 0-indexed
        if (month >= 4) {
            const nextYear = (year + 1).toString().slice(-2);
            return `${year}-${nextYear}`;
        } else {
            const prevYear = year - 1;
            const currentYearSuffix = year.toString().slice(-2);
            return `${prevYear}-${currentYearSuffix}`;
        }
    }

    async function loadInvoiceList() {
        const tbody = document.getElementById('invoice-list-body');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Loading...</td></tr>';

        try {
            const res = await fetch(`${API_BASE}/invoices`);
            const invoices = await res.json();

            // Handle FY Filtering
            const fyFilter = document.getElementById('history-fy-filter');
            const selectedFY = fyFilter ? fyFilter.value : 'all';
            
            // Collect all available FYs for the dropdown
            const availableFYs = new Set();
            invoices.forEach(inv => {
                if (inv.invoice_date) {
                    const fy = getFinancialYear(inv.invoice_date);
                    if (fy) availableFYs.add(fy);
                }
            });

            if (fyFilter && fyFilter.options.length <= 1) { // Only populate if empty (except 'All')
                Array.from(availableFYs).sort().reverse().forEach(fy => {
                    const opt = document.createElement('option');
                    opt.value = fy;
                    opt.textContent = `FY ${fy}`;
                    fyFilter.appendChild(opt);
                });
                $(fyFilter).off('change').on('change', () => loadInvoiceList());
            }

            if (!invoices.length) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#888;">No invoices yet. <a href="#" onclick="navigateTo(\'invoice-new\')">Create one!</a></td></tr>';
                return;
            }

            // Filter invoices by FY
            const filteredInvoices = selectedFY === 'all' 
                ? invoices 
                : invoices.filter(inv => getFinancialYear(inv.invoice_date) === selectedFY);

            if (!filteredInvoices.length) {
                tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;color:#888;">No invoices found for FY ${selectedFY}.</td></tr>`;
                return;
            }

            tbody.innerHTML = '';

            for (const inv of filteredInvoices) {
                // Fetch receipts for this invoice
                let amountPaid = 0;
                try {
                    const rRes = await fetch(`${API_BASE}/invoices/${inv.id}/receipts`);
                    const receipts = await rRes.json();
                    amountPaid = receipts.reduce((sum, r) => sum + r.amount, 0);
                } catch (e) { }

                const grandTotal = parseFloat(inv.grand_total || 0);
                const balance = grandTotal - amountPaid;

                let statusBadge = '<span class="badge" style="background:#4CAF50;color:white;padding:2px 6px;border-radius:4px;font-size:10px;">PAID</span>';
                if (balance > 0 && amountPaid > 0) {
                    statusBadge = '<span class="badge" style="background:#FF9800;color:white;padding:2px 6px;border-radius:4px;font-size:10px;">PARTIAL</span>';
                } else if (balance > 0) {
                    statusBadge = '<span class="badge" style="background:#F44336;color:white;padding:2px 6px;border-radius:4px;font-size:10px;">UNPAID</span>';
                }

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${inv.invoice_no}</strong></td>
                    <td>${inv.invoice_date || '-'}</td>
                    <td>${inv.client_name || '-'}</td>
                    <td style="text-align:right; white-space: nowrap;">&#8377;&nbsp;${parseFloat(inv.total_taxable_value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td style="text-align:right; white-space: nowrap;">&#8377;&nbsp;${parseFloat(inv.total_tax_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td style="text-align:right; white-space: nowrap;"><strong>&#8377;&nbsp;${grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong></td>
                    <td style="text-align:center;">${statusBadge}</td>
                    <td style="white-space: nowrap;">
                        <button class="btn btn-secondary" title="Generate PDF" style="padding:4px 8px;font-size:12px;margin-right:2px;" onclick="downloadInvoicePdf('${inv.id}','${inv.invoice_no}')"><i class="fas fa-file-pdf"></i></button>
                        ${balance > 0 ? `<button class="btn btn-primary" title="Add Payment" style="padding:4px 8px;font-size:12px;margin-right:2px;" onclick="openPaymentModal('${inv.id}', ${balance})"><i class="fas fa-coins"></i></button>` : ''}
                        <button class="btn btn-link" title="Delete Invoice" style="color:#e53935;padding:4px 8px;font-size:12px;" onclick="deleteInvoice('${inv.id}')"><i class="fas fa-trash"></i></button>
                    </td>
                `;
                tbody.appendChild(tr);
            }
        } catch (e) { tbody.innerHTML = '<tr><td colspan="8" style="color:red;">Failed to load.</td></tr>'; }
    }

    // --- PAYMENT MODAL LOGIC ---
    window.openPaymentModal = function (invoiceId, balanceDue) {
        document.getElementById('payment-invoice-id').value = invoiceId;
        document.getElementById('payment-amount').value = balanceDue.toFixed(2);
        document.getElementById('payment-amount').max = balanceDue.toFixed(2); // prevent overpayment
        document.getElementById('payment-date').value = new Date().toISOString().split('T')[0];
        document.getElementById('payment-method').value = 'Online';
        document.getElementById('payment-notes').value = '';
        document.getElementById('payment-modal').style.display = 'flex';
    };

    window.closePaymentModal = function () {
        document.getElementById('payment-modal').style.display = 'none';
    };

    window.submitPayment = async function (e) {
        e.preventDefault();
        const btn = document.getElementById('btn-submit-payment');
        btn.disabled = true;
        btn.innerText = 'Saving...';

        const invoiceId = document.getElementById('payment-invoice-id').value;
        const payload = {
            amount: parseFloat(document.getElementById('payment-amount').value),
            payment_date: document.getElementById('payment-date').value,
            payment_method: document.getElementById('payment-method').value,
            notes: document.getElementById('payment-notes').value
        };

        try {
            const res = await fetch(`${API_BASE}/invoices/${invoiceId}/receipt`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!res.ok) throw new Error(await res.text());

            showToast('Payment recorded successfully!');
            closePaymentModal();
            loadInvoiceList(); // refresh the table
        } catch (err) {
            alert('Failed to save payment: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.innerText = 'Save Receipt';
        }
    };

    async function downloadInvoicePdf(id, invoiceNo) {
        showToast('Generating PDF, please wait...', 'info');
        try {
            const res = await fetch(`${API_BASE}/invoices/${id}/pdf`);
            if (!res.ok) throw new Error(await res.text());
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Invoice_${invoiceNo.replace(/\//g, '_')}.pdf`;
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast('PDF downloaded!');
        } catch (e) { showToast('PDF failed: ' + e.message, 'error'); }
    }

    async function deleteInvoice(id) {
        if (!confirm('Delete this invoice? This cannot be undone.')) return;
        try {
            const res = await fetch(`${API_BASE}/invoices/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error((await res.json()).detail);
            showToast('Invoice deleted.'); loadInvoiceList();
        } catch (e) { showToast('Delete failed: ' + e.message, 'error'); }
    }

    function partyInfoHtml(p, addrLine1Key, addrLine2Key) {
        if (!p) return '';
        const name = p.name || p.branch_name || '';
        const addr1 = p[addrLine1Key] || p.address_line_1 || '';
        const addr2 = p[addrLine2Key] || p.address_line_2 || '';
        const gstin = p.gstin || '';
        
        let html = `<div style="font-size:12px;line-height:1.5;"><strong>${name}</strong>`;
        if (addr1) html += `<br>${addr1}`;
        if (addr2) html += `, ${addr2}`;
        if (p.city) html += `<br>${p.city}`;
        if (p.pincode) html += ` - ${p.pincode}`;
        if (p.state_name) html += `<br>${p.state_name}`;
        if (p.state_code) html += ` (${p.state_code})`;
        if (gstin) html += `<br><small>GSTIN: ${gstin}</small>`;
        html += `</div>`;
        return html;
    }

    async function openNewInvoice() {
        document.getElementById('invoice-items-body').innerHTML = '';
        document.getElementById('invoice-form').reset();
        _invoiceItemIdx = 0;
        recalcInvoiceTotals();
        const today = new Date().toISOString().slice(0, 10);
        document.getElementById('inv-invoice-date').value = today;
        try {
            const nr = await fetch(`${API_BASE}/invoices/next-number`);
            const nd = await nr.json();
            document.getElementById('inv-invoice-no').value = nd.invoice_no;
        } catch (e) { }

        // Seller dropdown
        const companySel = document.getElementById('inv-company-select');
        if (!companySel) return; 
        if ($(companySel).hasClass('select2-hidden-accessible')) $(companySel).select2('destroy');
        companySel.innerHTML = '';
        try {
            const cr = await fetch(`${API_BASE}/profiles`);
            const companies = await cr.json();
            if (Array.isArray(companies)) {
                companies.forEach(c => { const o = new Option(c.name, c.id, c.is_default, c.is_default); companySel.appendChild(o); });
                $(companySel).select2({ placeholder: '-- Select Seller --', width: '100%' });
                const def = companies.find(c => c.is_default) || companies[0];
                const sellerInfoEl = document.getElementById('inv-seller-info');
                if (def && sellerInfoEl) sellerInfoEl.innerHTML = partyInfoHtml(def, 'address_line_1', 'address_line_2');
                
                $(companySel).off('select2:select').on('select2:select', async function (e) {
                    const cr2 = await fetch(`${API_BASE}/profiles/${e.params.data.id}`);
                    const comp = await cr2.json();
                    if (sellerInfoEl) sellerInfoEl.innerHTML = partyInfoHtml(comp, 'address_line_1', 'address_line_2');
                    recalcInvoiceTotals();
                });
            }
        } catch (e) { console.error("Seller init error", e); }

        // Client dropdown
        const clientSel = document.getElementById('inv-client-select');
        if (!clientSel) return;
        if ($(clientSel).hasClass('select2-hidden-accessible')) $(clientSel).select2('destroy');
        clientSel.innerHTML = '<option value="">-- Select Client --</option>';
        const shipSel = document.getElementById('inv-shipping-select');
        if (shipSel && $(shipSel).hasClass('select2-hidden-accessible')) $(shipSel).select2('destroy');
        if (shipSel) {
            shipSel.innerHTML = '<option value="">-- Same as Billing --</option>';
            $(shipSel).select2({ placeholder: '-- Select client first --', allowClear: true, width: '100%' });
        }
        try {
            const cr2 = await fetch(`${API_BASE}/clients`);
            const clients = await cr2.json();
            if (Array.isArray(clients)) {
                clients.forEach(c => clientSel.appendChild(new Option(c.name, c.id)));
                $(clientSel).select2({ placeholder: '-- Select Client --', allowClear: true, width: '100%' });
                $(clientSel).off('select2:select select2:unselect').on('select2:select', async function (e) {
                    const cid = e.params.data.id;
                    const cr3 = await fetch(`${API_BASE}/clients/${cid}`);
                    const client = await cr3.json();
                    const buyerInfoEl = document.getElementById('inv-buyer-info');
                    const consigneeInfoEl = document.getElementById('inv-consignee-info');
                    
                    if (buyerInfoEl) buyerInfoEl.innerHTML = partyInfoHtml(client, 'billing_address_line_1', 'billing_address_line_2');
                    if (consigneeInfoEl) {
                        consigneeInfoEl.innerHTML = '<em style="font-size:11px;color:#888;">Same as Billing Address</em><br>' +
                                                    partyInfoHtml(client, 'billing_address_line_1', 'billing_address_line_2');
                    }
                    
                    if (shipSel) {
                        if ($(shipSel).hasClass('select2-hidden-accessible')) $(shipSel).select2('destroy');
                        shipSel.innerHTML = '<option value="">-- Same as Billing --</option>';
                        const sr = await fetch(`${API_BASE}/clients/${cid}/shipping`);
                        const addrs = await sr.json();
                        addrs.forEach(s => shipSel.appendChild(new Option(s.branch_name || s.address_line_1, s.id)));
                        $(shipSel).select2({ placeholder: '-- Same as Billing --', allowClear: true, width: '100%' });
                        $(shipSel).off('select2:select select2:unselect').on('select2:select', async function (e2) {
                            const sr2 = await fetch(`${API_BASE}/shipping/${e2.params.data.id}`);
                            const ship = await sr2.json();
                            if (consigneeInfoEl) consigneeInfoEl.innerHTML = partyInfoHtml(ship, 'address_line_1', 'address_line_2');
                            recalcInvoiceTotals();
                        }).on('select2:unselect', function () {
                            if (consigneeInfoEl) {
                                consigneeInfoEl.innerHTML = '<em style="font-size:11px;color:#888;">Same as Billing Address</em><br>' +
                                                            partyInfoHtml(client, 'billing_address_line_1', 'billing_address_line_2');
                            }
                            recalcInvoiceTotals();
                        });
                    }
                    recalcInvoiceTotals();
                }).on('select2:unselect', function () {
                    const buyerInfoEl = document.getElementById('inv-buyer-info');
                    const consigneeInfoEl = document.getElementById('inv-consignee-info');
                    if (buyerInfoEl) buyerInfoEl.innerHTML = '';
                    if (consigneeInfoEl) consigneeInfoEl.innerHTML = '';
                    if (shipSel) {
                        if ($(shipSel).hasClass('select2-hidden-accessible')) $(shipSel).select2('destroy');
                        shipSel.innerHTML = '<option value="">-- Same as Billing --</option>';
                        $(shipSel).select2({ placeholder: '-- Select client first --', allowClear: true, width: '100%' });
                    }
                    recalcInvoiceTotals();
                });
            }
        } catch (e) { console.error("Client init error", e); }

        _invoiceItemRowAdder();  // add first blank row
        document.getElementById('invoice-form').onsubmit = submitInvoice;
    }

    let _invoiceItemIdx = 0;
    function _invoiceItemRowAdder() {
        const tbody = document.getElementById('invoice-items-body');
        const rowNum = tbody.rows.length + 1;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style="text-align:center;">${rowNum}</td>
            <td><input type="text" class="inv-item-desc" placeholder="Description of goods / service" style="width:100%;box-sizing:border-box;padding:4px;border:1px solid #ccc;border-radius:4px;"></td>
            <td><input type="text" class="inv-item-hsn" placeholder="HSN" style="width:100%;padding:4px;border:1px solid #ccc;border-radius:4px;"></td>
            <td><input type="number" class="inv-item-qty" min="0" step="any" placeholder="0" style="width:100%;padding:4px;border:1px solid #ccc;border-radius:4px;" oninput="recalcRow(this)"></td>
            <td><input type="text" class="inv-item-unit" placeholder="NOS" style="width:100%;padding:4px;border:1px solid #ccc;border-radius:4px;"></td>
            <td><input type="number" class="inv-item-rate" min="0" step="any" placeholder="0.00" style="width:100%;padding:4px;border:1px solid #ccc;border-radius:4px;" oninput="recalcRow(this)"></td>
            <td class="inv-item-taxable" style="text-align:right;padding-right:8px;">0.00</td>
            <td><select class="inv-item-gst" style="width:100%;padding:4px;border:1px solid #ccc;border-radius:4px;" onchange="recalcRow(this)">
                <option value="0">0%</option><option value="5">5%</option><option value="12">12%</option>
                <option value="18" selected>18%</option><option value="28">28%</option>
            </select></td>
            <td class="inv-item-tax" style="text-align:right;padding-right:8px;">0.00</td>
            <td><button type="button" onclick="removeInvoiceRow(this)" style="background:none;border:none;color:#e53935;cursor:pointer;font-size:16px;"><i class="fas fa-times"></i></button></td>
        `;
        tbody.appendChild(tr);
    }
    // Expose immediately after definition — NOT inside the function body
    window.addInvoiceItem = _invoiceItemRowAdder;
    window._invoiceItemRowAdder = _invoiceItemRowAdder;

    function recalcInvoiceTotals() {
        let totalTaxable = 0, totalTax = 0;
        document.querySelectorAll('#invoice-items-body tr').forEach(row => {
            totalTaxable += parseFloat(row.querySelector('.inv-item-taxable')?.textContent || 0);
            totalTax += parseFloat(row.querySelector('.inv-item-tax')?.textContent || 0);
        });
        const gt = totalTaxable + totalTax;
        document.getElementById('inv-total-taxable').textContent = '\u20b9 ' + totalTaxable.toFixed(2);
        document.getElementById('inv-total-tax').textContent = '\u20b9 ' + totalTax.toFixed(2);
        document.getElementById('inv-grand-total').textContent = '\u20b9 ' + gt.toFixed(2);
        const badge = document.getElementById('inv-tax-type-badge');
        if (badge) {
            const st = document.getElementById('inv-seller-info')?.textContent || '';
            const bt = document.getElementById('inv-buyer-info')?.textContent || '';
            const sm = st.match(/\((\d+)\)/); const bm = bt.match(/\((\d+)\)/);
            if (sm && bm) {
                badge.innerHTML = sm[1] !== bm[1]
                    ? '<i class="fas fa-info-circle" style="color:#2196f3;"></i> <strong>Inter-state supply:</strong> IGST will apply'
                    : '<i class="fas fa-info-circle" style="color:#4caf50;"></i> <strong>Intra-state supply:</strong> CGST + SGST will apply';
            } else { badge.innerHTML = ''; }
        }
    }

    async function submitInvoice(e) {
        e.preventDefault();
        const fd = new FormData(document.getElementById('invoice-form'));
        const clientId = document.getElementById('inv-client-select').value;
        if (!clientId) { showToast('Please select a buyer / client.', 'error'); return; }
        const shippingId = document.getElementById('inv-shipping-select').value || null;
        const companyId = document.getElementById('inv-company-select').value || null;
        const items = [];
        let allOk = true;
        document.querySelectorAll('#invoice-items-body tr').forEach(row => {
            const desc = row.querySelector('.inv-item-desc').value.trim();
            if (!desc) { allOk = false; return; }
            const qty = parseFloat(row.querySelector('.inv-item-qty').value) || 0;
            const rate = parseFloat(row.querySelector('.inv-item-rate').value) || 0;
            const gst = parseFloat(row.querySelector('.inv-item-gst').value) || 0;
            const taxable = qty * rate;
            const tax = taxable * gst / 100;
            items.push({
                description: desc, hsn_sac: row.querySelector('.inv-item-hsn').value.trim(),
                quantity: qty, unit: row.querySelector('.inv-item-unit').value.trim() || 'NOS',
                rate, taxable_value: taxable, igst_rate: gst, cgst_rate: gst / 2, sgst_rate: gst / 2,
                tax_amount: tax, total_amount: taxable + tax
            });
        });
        if (!allOk || !items.length) { showToast('Add at least one item with a description.', 'error'); return; }
        let totalTaxable = 0, totalTax = 0;
        items.forEach(i => { totalTaxable += i.taxable_value; totalTax += i.tax_amount; });
        const payload = {
            invoice_no: fd.get('invoice_no'), invoice_date: fd.get('invoice_date'),
            eway_bill_no: fd.get('eway_bill_no') || null, payment_mode_terms: fd.get('payment_mode_terms') || null,
            reference_no: fd.get('reference_no') || null, other_references: fd.get('other_references') || null,
            buyers_order_no: fd.get('buyers_order_no') || null, order_date: fd.get('order_date') || null,
            delivery_note: fd.get('delivery_note') || null, delivery_note_date: fd.get('delivery_note_date') || null,
            terms_of_delivery: fd.get('terms_of_delivery') || null, dispatch_doc_no: fd.get('dispatch_doc_no') || null,
            dispatched_through: fd.get('dispatched_through') || null, destination: fd.get('destination') || null,
            company_id: companyId, client_id: clientId, shipping_id: shippingId,
            total_taxable_value: totalTaxable, total_tax_amount: totalTax, grand_total: totalTaxable + totalTax, items
        };
        const btn = document.getElementById('btn-save-invoice');
        btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        try {
            const res = await fetch(`${API_BASE}/invoices`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            if (!res.ok) throw new Error((await res.json()).detail);
            const data = await res.json();
            
            // Auto-trigger PDF download
            await downloadInvoicePdf(data.invoice_id, payload.invoice_no);
            
            showToast('Invoice saved successfully.', 'success', () => {
                navigateTo('invoice-list');
            });
        } catch (e) { showToast('Save failed: ' + e.message, 'error'); }
        finally { btn.disabled = false; btn.innerHTML = '<i class="fas fa-save"></i> Save Invoice'; }
    }

    function _invoiceOpenNewProxy() { return openNewInvoice(); }

    window.clearInvoiceForm = function() {
        if (!confirm("Clear all data in this invoice?")) return;
        const form = document.getElementById('invoice-form');
        const body = document.getElementById('invoice-items-body');
        if (form) form.reset();
        if (body) {
            body.innerHTML = '';
            _invoiceItemRowAdder(); // Add back one blank row
        }
        recalcInvoiceTotals();
    };

    // Init — expose navigateTo globally BEFORE first call so inline onclick works
    window.navigateTo = navigateTo;
    navigateTo(state.currentPage);
});


// ---- Global onclick wrappers for invoice inline HTML ----
function recalcRow(input) {
    const row = input.closest('tr');
    const qty = parseFloat(row.querySelector('.inv-item-qty').value) || 0;
    const rate = parseFloat(row.querySelector('.inv-item-rate').value) || 0;
    const gst = parseFloat(row.querySelector('.inv-item-gst').value) || 0;
    const taxable = qty * rate;
    const tax = taxable * gst / 100;
    row.querySelector('.inv-item-taxable').textContent = taxable.toFixed(2);
    row.querySelector('.inv-item-tax').textContent = tax.toFixed(2);
    // Update totals
    let tt = 0, tx = 0;
    document.querySelectorAll('#invoice-items-body tr').forEach(r => {
        tt += parseFloat(r.querySelector('.inv-item-taxable')?.textContent || 0);
        tx += parseFloat(r.querySelector('.inv-item-tax')?.textContent || 0);
    });
    document.getElementById('inv-total-taxable').textContent = '\u20b9 ' + tt.toFixed(2);
    document.getElementById('inv-total-tax').textContent = '\u20b9 ' + tx.toFixed(2);
    document.getElementById('inv-grand-total').textContent = '\u20b9 ' + (tt + tx).toFixed(2);
}
function addInvoiceItem() {
    console.log("addInvoiceItem called!");
    // Fully self-contained — no dependency on inner-scoped functions
    const tbody = document.getElementById('invoice-items-body');
    if (!tbody) { console.error("No tbody found"); return; }
    const rowNum = tbody.rows.length + 1;
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td style="text-align:center;">${rowNum}</td>
        <td><input type="text" class="inv-item-desc" placeholder="Description of goods / service" style="width:100%;box-sizing:border-box;padding:4px;border:1px solid #ccc;border-radius:4px;"></td>
        <td><input type="text" class="inv-item-hsn" placeholder="HSN" style="width:100%;padding:4px;border:1px solid #ccc;border-radius:4px;"></td>
        <td><input type="number" class="inv-item-qty" min="0" step="any" placeholder="0" style="width:100%;padding:4px;border:1px solid #ccc;border-radius:4px;" oninput="recalcRow(this)"></td>
        <td><input type="text" class="inv-item-unit" placeholder="NOS" style="width:100%;padding:4px;border:1px solid #ccc;border-radius:4px;"></td>
        <td><input type="number" class="inv-item-rate" min="0" step="any" placeholder="0.00" style="width:100%;padding:4px;border:1px solid #ccc;border-radius:4px;" oninput="recalcRow(this)"></td>
        <td class="inv-item-taxable" style="text-align:right;padding-right:8px;">0.00</td>
        <td><select class="inv-item-gst" style="width:100%;padding:4px;border:1px solid #ccc;border-radius:4px;" onchange="recalcRow(this)">
            <option value="0">0%</option><option value="5">5%</option><option value="12">12%</option>
            <option value="18" selected>18%</option><option value="28">28%</option>
        </select></td>
        <td class="inv-item-tax" style="text-align:right;padding-right:8px;">0.00</td>
        <td><button type="button" onclick="removeInvoiceRow(this)" style="background:none;border:none;color:#e53935;cursor:pointer;font-size:16px;"><i class="fas fa-times"></i></button></td>
    `;
    tbody.appendChild(tr);
}
function removeInvoiceRow(btn) {
    btn.closest('tr').remove();
    const tbody = document.getElementById('invoice-items-body');
    [...tbody.rows].forEach((r, i) => r.cells[0].textContent = i + 1);
    let tt = 0, tx = 0;
    document.querySelectorAll('#invoice-items-body tr').forEach(r => {
        tt += parseFloat(r.querySelector('.inv-item-taxable')?.textContent || 0);
        tx += parseFloat(r.querySelector('.inv-item-tax')?.textContent || 0);
    });
    document.getElementById('inv-total-taxable').textContent = '\u20b9 ' + tt.toFixed(2);
    document.getElementById('inv-total-tax').textContent = '\u20b9 ' + tx.toFixed(2);
    document.getElementById('inv-grand-total').textContent = '\u20b9 ' + (tt + tx).toFixed(2);
}
function downloadInvoicePdf(id, no) {
    const event = new CustomEvent('invoice:download-pdf', { detail: { id, no } });
    document.dispatchEvent(event);
}
function deleteInvoice(id) {
    document.dispatchEvent(new CustomEvent('invoice:delete', { detail: { id } }));
}
document.addEventListener('invoice:download-pdf', async e => {
    const { id, no } = e.detail;
    showToast('Generating PDF, please wait...', 'info');
    try {
        const res = await fetch(`/api/invoices/${id}/pdf`);
        if (!res.ok) throw new Error(await res.text());
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `Invoice_${no.replace(/\//g, '_')}.pdf`;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        // Close the "Generating" modal and show success (or just show success)
        showToast('PDF Downloaded!', 'success');
    } catch (ex) {
        showToast('PDF error: ' + ex.message, 'error');
    }
});
document.addEventListener('invoice:delete', async e => {
    if (!confirm('Delete this invoice permanently?')) return;
    const res = await fetch(`/api/invoices/${e.detail.id}`, { method: 'DELETE' });
    if (res.ok) {
        showToast('Invoice deleted successfully.');
        if (typeof loadInvoiceList === 'function') loadInvoiceList();
    }
});

// ==============================================================
//  SETTINGS / DATA MANAGEMENT (Backup & Restore)
// ==============================================================

window.downloadBackup = async function () {
    showToast('Generating backup... please wait', 'info');

    try {
        const res = await fetch('/api/backup');
        if (!res.ok) throw new Error(await res.text());

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        
        // Try to get filename from header
        const disposition = res.headers.get('Content-Disposition');
        let filename = `Backup_${new Date().toISOString().replace(/[:.]/g, '-')}.zip`;
        if (disposition && disposition.indexOf('attachment') !== -1) {
            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            const matches = filenameRegex.exec(disposition);
            if (matches != null && matches[1]) {
                filename = matches[1].replace(/['"]/g, '');
            }
        }

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        if (url) {
            showToast('Backup Downloaded!');
        }
    } catch (e) {
        console.error("Backup failed:", e);
        showToast('Backup failed: ' + e.message, 'error');
    }
};

let selectedRestoreFile = null;

window.handleRestoreSelection = function (event) {
    const file = event.target.files[0];
    if (file) {
        selectedRestoreFile = file;
        document.getElementById('restore-file-name').innerText = file.name;
        document.getElementById('btn-restore-db').disabled = false;
    } else {
        selectedRestoreFile = null;
        document.getElementById('restore-file-name').innerText = '';
        document.getElementById('btn-restore-db').disabled = true;
    }
};

window.uploadRestore = async function () {
    if (!selectedRestoreFile) return;

    if (!confirm("WARNING: This will overwrite your current database. Any changes made after this backup was created will be permanently lost. Are you sure you want to proceed?")) {
        return;
    }

    const formData = new FormData();
    formData.append('file', selectedRestoreFile);

    const btn = document.getElementById('btn-restore-db');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Restoring...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/restore', {
            method: 'POST',
            body: formData
        });

        if (res.ok) {
            showToast('Database restored successfully! Reloading...');
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            const err = await res.json();
            showToast(err.detail || 'Error restoring database', 'error');
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch (e) {
        console.error("Restore failed:", e);
        showToast('Network error during restore', 'error');
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};
