/**
 * VPN Leak Test - Client-side detection
 */

// WebRTC IP detection
async function getWebRTCIPs() {
    const ips = [];
    
    try {
        const pc = new RTCPeerConnection({
            iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
        });
        
        pc.createDataChannel('');
        
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        
        await new Promise(resolve => {
            pc.onicecandidate = (ice) => {
                if (!ice || !ice.candidate || !ice.candidate.candidate) {
                    resolve();
                    return;
                }
                
                const candidate = ice.candidate.candidate;
                const ipMatch = /([0-9]{1,3}\.){3}[0-9]{1,3}/.exec(candidate);
                
                if (ipMatch && !ips.includes(ipMatch[1])) {
                    ips.push(ipMatch[1]);
                }
            };
            
            setTimeout(resolve, 2000);
        });
        
        pc.close();
    } catch (e) {
        console.error('WebRTC detection failed:', e);
    }
    
    return ips;
}

// Check if IP is private
function isPrivateIP(ip) {
    const parts = ip.split('.').map(Number);
    if (parts[0] === 10) return true;
    if (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) return true;
    if (parts[0] === 192 && parts[1] === 168) return true;
    if (parts[0] === 127) return true;
    return false;
}

// Run full test
async function runTest() {
    const btn = document.getElementById('startTest');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    
    btn.disabled = true;
    loading.classList.add('active');
    results.classList.remove('active');
    
    // Get WebRTC IPs
    const webrtcIPs = await getWebRTCIPs();
    
    // Send to server for analysis
    try {
        const response = await fetch('/api/vpn/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ webrtc_ips: webrtcIPs })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayResults(data.result, webrtcIPs);
        } else {
            showError('Test failed: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        showError('Network error: ' + e.message);
    } finally {
        loading.classList.remove('active');
        btn.disabled = false;
    }
}

function showError(msg) {
    const container = document.getElementById('results');
    container.innerHTML = '<div class="alert alert-danger">' + msg + '</div>';
    container.classList.add('active');
}

// Display results
function displayResults(result, webrtcIPs) {
    const container = document.getElementById('results');
    const score = result.privacy_score;
    const gradeClass = score.grade.toLowerCase();
    
    let html = `
        <div class="score-card">
            <div class="grade ${gradeClass}">${score.grade}</div>
            <div class="score-value ${gradeClass}">${score.score}</div>
            <div style="color: #64748b;">Anonymity Score (0-100)</div>
        </div>
    `;
    
    // Alerts
    if (score.issues.length > 0) {
        score.issues.forEach(issue => {
            html += `<div class="alert alert-danger">[WARNING] ${issue}</div>`;
        });
    }
    
    if (result.vpn_status === 'disabled') {
        html += `<div class="alert alert-warning">[WARNING] No VPN detected - your real IP is exposed</div>`;
    } else if (result.vpn_status === 'installed_not_active') {
        html += `<div class="alert alert-warning">[WARNING] VPN is installed but not connected</div>`;
    }
    
    // Info grid
    html += '<div class="info-grid">';
    
    // Public IP card
    html += `
        <div class="info-card">
            <h3>Public IP Address</h3>
            <div class="ip-address">${result.public_ip.ipv4[0] || 'Unknown'}</div>
            ${result.public_ip.ipv4.length > 1 ? '<div style="color: #f59e0b; font-size: 13px; margin-top: 5px;">[WARNING] Multiple IPs detected</div>' : ''}
            ${result.geolocation ? `
                <div class="detail-row">
                    <span class="detail-label">Country</span>
                    <span class="detail-value">${result.geolocation.country} (${result.geolocation.country_code})</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">City</span>
                    <span class="detail-value">${result.geolocation.city}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">ISP</span>
                    <span class="detail-value">${result.geolocation.isp}</span>
                </div>
            ` : ''}
        </div>
    `;
    
    // VPN Status card
    const vpnStatus = result.vpn_status;
    let vpnStatusText = 'Not detected';
    let vpnStatusClass = 'danger';
    
    if (vpnStatus === 'active') {
        vpnStatusText = 'Active';
        vpnStatusClass = 'success';
    } else if (vpnStatus === 'installed_not_active') {
        vpnStatusText = 'Installed (not active)';
        vpnStatusClass = 'warning';
    } else if (vpnStatus === 'possible_via_network') {
        vpnStatusText = 'Possible (network)';
        vpnStatusClass = 'info';
    }
    
    html += `
        <div class="info-card">
            <h3>VPN Status</h3>
            <div class="status-indicator ${vpnStatusClass}">
                <span class="dot ${vpnStatusClass}"></span>
                ${vpnStatusText}
            </div>
            ${result.vpn_interfaces.total_detected > 0 ? `
                <div style="margin-top: 15px;">
                    <div style="color: #64748b; font-size: 13px; margin-bottom: 5px;">Detected interfaces:</div>
                    ${result.vpn_interfaces.active.map(i => '<div style="color: #10b981; font-size: 13px;">[ACTIVE] ' + i.name + '</div>').join('')}
                    ${result.vpn_interfaces.inactive.map(i => '<div style="color: #64748b; font-size: 13px;">[INACTIVE] ' + i.name + '</div>').join('')}
                </div>
            ` : ''}
        </div>
    `;
    
    // WebRTC card
    const webrtc = result.webrtc;
    let webrtcStatus = 'info';
    let webrtcText = 'Not checked';
    
    if (webrtc.leak_detected) {
        webrtcStatus = 'danger';
        webrtcText = 'LEAK DETECTED!';
    } else if (webrtc.status === 'success') {
        webrtcStatus = 'success';
        webrtcText = 'No leak';
    }
    
    html += `
        <div class="info-card">
            <h3>WebRTC Leak Test</h3>
            <div class="status-indicator ${webrtcStatus}">
                <span class="dot ${webrtcStatus}"></span>
                ${webrtcText}
            </div>
            ${webrtcIPs.length > 0 ? `
                <div style="margin-top: 15px;">
                    <div style="color: #64748b; font-size: 13px; margin-bottom: 5px;">Detected IPs:</div>
                    <div class="webrtc-ips">
                        ${webrtcIPs.map(ip => {
                            const isPrivate = isPrivateIP(ip);
                            const isLeak = webrtc.leak_detected && webrtc.exposed_ips.includes(ip);
                            let className = isLeak ? 'leak' : isPrivate ? 'private' : 'public';
                            let label = isLeak ? 'LEAK' : isPrivate ? 'private' : 'public';
                            return '<span class="ip-tag ' + className + '">' + ip + ' (' + label + ')</span>';
                        }).join('')}
                    </div>
                </div>
            ` : '<div style="color: #64748b; font-size: 13px; margin-top: 10px;">WebRTC IPs not detected</div>'}
        </div>
    `;
    
    html += '</div>';
    
    // Recommendations
    if (result.recommendations && result.recommendations.length > 0) {
        html += `
            <div class="recommendations">
                <h3>Recommendations</h3>
                <ul>
                    ${result.recommendations.map(r => '<li>' + r + '</li>').join('')}
                </ul>
            </div>
        `;
    }
    
    container.innerHTML = html;
    container.classList.add('active');
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('startTest');
    if (btn) {
        btn.addEventListener('click', runTest);
    }
});
