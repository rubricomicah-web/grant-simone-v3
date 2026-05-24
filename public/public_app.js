const api='/api';let token=localStorage.getItem('token')||'';let profiles=[];let currentUser=null;let activePreviewPlan=null;let realFeatures=null;let activeWorkflowId=null;let activeWorkflowReady=false;const $=id=>document.getElementById(id);

const US_STATE_OPTIONS = [
 ["", "All USA / National"],
 ["Alabama", "Alabama"], ["Alaska", "Alaska"], ["Arizona", "Arizona"], ["Arkansas", "Arkansas"],
 ["California", "California"], ["Colorado", "Colorado"], ["Connecticut", "Connecticut"], ["Delaware", "Delaware"],
 ["District of Columbia", "District of Columbia"], ["Florida", "Florida"], ["Georgia", "Georgia"], ["Hawaii", "Hawaii"],
 ["Idaho", "Idaho"], ["Illinois", "Illinois"], ["Indiana", "Indiana"], ["Iowa", "Iowa"], ["Kansas", "Kansas"],
 ["Kentucky", "Kentucky"], ["Louisiana", "Louisiana"], ["Maine", "Maine"], ["Maryland", "Maryland"],
 ["Massachusetts", "Massachusetts"], ["Michigan", "Michigan"], ["Minnesota", "Minnesota"], ["Mississippi", "Mississippi"],
 ["Missouri", "Missouri"], ["Montana", "Montana"], ["Nebraska", "Nebraska"], ["Nevada", "Nevada"],
 ["New Hampshire", "New Hampshire"], ["New Jersey", "New Jersey"], ["New Mexico", "New Mexico"], ["New York", "New York"],
 ["North Carolina", "North Carolina"], ["North Dakota", "North Dakota"], ["Ohio", "Ohio"], ["Oklahoma", "Oklahoma"],
 ["Oregon", "Oregon"], ["Pennsylvania", "Pennsylvania"], ["Rhode Island", "Rhode Island"],
 ["South Carolina", "South Carolina"], ["South Dakota", "South Dakota"], ["Tennessee", "Tennessee"], ["Texas", "Texas"],
 ["Utah", "Utah"], ["Vermont", "Vermont"], ["Virginia", "Virginia"], ["Washington", "Washington"],
 ["West Virginia", "West Virginia"], ["Wisconsin", "Wisconsin"], ["Wyoming", "Wyoming"],
 ["Puerto Rico", "Puerto Rico"], ["Guam", "Guam"], ["U.S. Virgin Islands", "U.S. Virgin Islands"],
 ["American Samoa", "American Samoa"], ["Northern Mariana Islands", "Northern Mariana Islands"]
];
function populateStateDropdowns(){
 document.querySelectorAll('[data-state-select]').forEach(sel=>{
 const mode = sel.getAttribute('data-state-select');
 const first = mode === 'profile' ? ['','Select state / territory'] : ['','All USA / National'];
 const options = [first, ...US_STATE_OPTIONS.slice(1)];
 sel.innerHTML = options.map(([value,label])=>`<option value="${esc(value)}">${esc(label)}</option>`).join('');
 });
}

function toast(msg){$('toast').textContent=msg;$('toast').classList.remove('hidden');setTimeout(()=>$('toast').classList.add('hidden'),2600)}
function msg(text,err=false){$('authMessage').textContent=text;$('authMessage').className='msg'+(err?' error':'')}
function clearMsg(){$('authMessage').className='msg hidden';$('authMessage').textContent=''}
const PLAN_LABELS={individual_elite:'Individual Elite - $99/mo',business_owner:'Business Owner - $299/mo',white_label_platform:'White Label Platform - $5,000/yr',individual_starter:'Individual Elite - $99/mo',individual_pro:'Individual Elite - $99/mo',business_growth:'Business Owner - $299/mo',business_scale:'Business Owner - $299/mo',business_enterprise:'Business Owner - $299/mo',white_label_agency:'White Label Platform - $5,000/yr',white_label_studio:'White Label Platform - $5,000/yr',white_label:'White Label Platform - $5,000/yr'};
const FEATURE_LABELS={grant_search:'Opportunity Radar',proposals:'Proposal Studio',workflows:'Funding Workflow',documents:'Document Vault',pdf_exports:'PDF Exports',private_grants:'Private/Corporate Grants',white_label:'White Label',admin:'Admin Controls',notifications:'Notifications',tracker:'Approval Center',profiles:'Funding Profiles',client_profile:'Client Profile'};
const PAGE_FEATURE={grants:'grant_search',proposals:'proposals',workflows:'workflows',documents:'documents',white:'white_label',admin:'admin',notifications:'notifications',apps:'tracker',profiles:'profiles',client:'client_profile'};
function showLogin(){clearMsg();$('loginPanel').classList.remove('hidden');$('signupPanel').classList.add('hidden');$('loginTab').classList.add('active');$('signupTab').classList.remove('active')}
function showSignup(){clearMsg();$('signupPanel').classList.remove('hidden');$('loginPanel').classList.add('hidden');$('signupTab').classList.add('active');$('loginTab').classList.remove('active');if(!$('signupPlan').value){$('signupButton').disabled=true;$('signupButton').textContent='Choose a Plan First';if($('selectedPlanBanner')){$('selectedPlanBanner').classList.remove('hidden');$('selectedPlanBanner').innerHTML='<strong>No plan selected.</strong><br><span class="mini">Please choose a plan from the pricing page before creating an account.</span><br><br><a class="btn secondary" href="/index.html#plans">Back to Plans</a>'}}}
function pickPlan(plan){location.href='/signup.html?plan='+encodeURIComponent(plan)}
function applySelectedPlan(plan){if(!plan||!PLAN_LABELS[plan]){if($('selectedPlanHero'))$('selectedPlanHero').innerHTML='<strong>No plan selected.</strong><br><span class="mini">Choose a plan on the pricing page to create your account.</span><br><br><a class="btn secondary" href="/index.html#plans">Back to Plans</a>';return}if($('signupPlan'))$('signupPlan').value=plan;if(plan.startsWith('business_')){$('accountType').value='business'}else if(plan.startsWith('white_label')){$('accountType').value='agency'}else{$('accountType').value='individual'}const label=PLAN_LABELS[plan];$('signupButton').disabled=false;$('signupButton').textContent='Create Account';if($('selectedPlanBanner')){$('selectedPlanBanner').classList.remove('hidden');$('selectedPlanBanner').innerHTML='<strong>Selected Plan:</strong> '+label+'<br><span class="mini">Your selected plan controls feature access. You can start after account creation.</span><br><br><a href="/index.html#plans">Change plan</a>'}if($('selectedPlanHero')){$('selectedPlanHero').innerHTML='<strong>Your selected plan:</strong> '+label+'<br><span class="mini">Create your account and start using Mogul Grant System.</span>'}}
function headers(){return {'Content-Type':'application/json','Authorization':'Bearer '+token}}
async function request(path,opts={}){const r=await fetch(api+path,{...opts,headers:{...headers(),...(opts.headers||{})}});let t=await r.text();let d={};try{d=t?JSON.parse(t):{}}catch(e){d={detail:t}}if(!r.ok){let detail=d.detail||t||'Request failed';if(Array.isArray(detail)){detail=detail.map(x=>x.msg||JSON.stringify(x)).join("\n")}throw new Error(detail)}return d}
async function enter(){document.title='Mogul Grant System Dashboard';if(location.pathname.includes('signup.html')||location.pathname==='/dashboard'){history.replaceState({},'', '/signup.html')}$('authShell').classList.add('hidden');$('app').classList.remove('hidden');await loadMe();loadProfiles();loadNotifications();loadFundingHealth();renderPipelineStepper([])}
function clearSession(){localStorage.removeItem('token');localStorage.removeItem('access_token');localStorage.removeItem('user');sessionStorage.clear();token='';currentUser=null;profiles=[]}
async function register(){try{clearSession();clearMsg();if(!$('signupPlan').value){msg('Please choose a plan from the pricing page first.',true);return}const password=$('signupPassword').value;if(password.length<8){msg('Password must be at least 8 characters.',true);return}if(!$('signupEmail').value.trim()){msg('Please enter your email address.',true);return}document.body.classList.add('loading');const workspaceName=$('tenantNameSignup').value.trim()||(($('signupName').value.trim()||'Mogul Grant System')+' Workspace');const body={email:$('signupEmail').value.trim(),password:password,full_name:$('signupName').value.trim()||'Member',tenant_slug:'default',tenant_name:workspaceName,account_type:$('accountType').value,plan:$('signupPlan').value};const d=await request('/auth/register',{method:'POST',body:JSON.stringify(body)});token=d.access_token;localStorage.setItem('token',token);if(d.payment_required && d.checkout_url){msg('Account created. Redirecting to secure checkout...');window.location.href=d.checkout_url}else{msg('Account created. You now have access.');toast('Welcome to Mogul Grant System.');enter()}}catch(e){msg(e.message,true)}finally{document.body.classList.remove('loading')}}
async function login(){try{clearSession();clearMsg();if(!$('loginEmail').value.trim()||!$('loginPassword').value){msg('Enter your email and password.',true);return}document.body.classList.add('loading');const body={email:$('loginEmail').value.trim(),password:$('loginPassword').value,tenant_slug:'default'};const d=await request('/auth/login',{method:'POST',body:JSON.stringify(body)});token=d.access_token;localStorage.setItem('token',token);enter();toast('Logged in')}catch(e){msg(e.message,true)}finally{document.body.classList.remove('loading')}}
function activeFeatures(){return (currentUser&&currentUser.features)||{}}
function featureAllowed(feature){if(!feature)return true;return !!activeFeatures()[feature]}
function formatLimit(v){return Number(v)>=999999?'Unlimited':esc(v??0)}
function renderUsage(u){if(!$('usageSummary'))return;const limits=(u&&u.limits)||{};const used=(u&&u.used)||{};const credits=(u&&u.credits)||{};const keys=[['grant_searches','Grant searches'],['proposals','Proposals'],['workflows','Workflows'],['documents','Document Vault'],['pdf_exports','PDF exports']];const creditTotal=Number(credits.total||0);const creditUsed=Number(credits.used||0);const creditRemaining=creditTotal>=999999?'Unlimited':Number(credits.remaining||0);let html='';if(activePreviewPlan){html+=`<div class="preview-banner"><strong>Preview mode:</strong> ${esc(PLAN_LABELS[activePreviewPlan]||activePreviewPlan)}<br><span class="mini">You are viewing the app as this plan. Your admin account is unchanged.</span><br><br><button type="button" class="btn secondary" onclick="exitPreviewMode()">Exit Preview Mode</button></div>`}html+=`<div class="usage-card"><span class="mini">Monthly credits</span><strong>${creditUsed} used</strong><div class="progress"><span style="width:${creditTotal>0&&creditTotal<999999?Math.min(100,Math.round((creditUsed/creditTotal)*100)):0}%"></span></div><p class="mini">Remaining: ${creditRemaining} • Resets: ${esc(credits.reset_date||'monthly')}</p></div>`;html+=keys.map(([k,label])=>{const lim=Number(limits[k]||0);const val=Number(used[k]||0);const pct=lim>0&&lim<999999?Math.min(100,Math.round((val/lim)*100)):0;return `<div class="usage-card"><span class="mini">${label}</span><strong>${val} / ${formatLimit(lim)}</strong><div class="progress"><span style="width:${pct}%"></span></div></div>`}).join('');html+=`<div class="usage-card"><span class="mini">Current plan</span><strong>${esc(PLAN_LABELS[u?.plan]||u?.label||u?.plan||'Plan')}</strong></div>`;$('usageSummary').innerHTML=html}
function applyPlanUI(){const features=activeFeatures();document.querySelectorAll('.nav button[data-page]').forEach(btn=>{const page=btn.dataset.page;const f=PAGE_FEATURE[page];const allowed=!f||features[f];btn.classList.toggle('hidden',!allowed);btn.classList.toggle('locked',!!f&&!allowed);});if($('adminNav'))$('adminNav').classList.toggle('hidden',!features.admin && !activePreviewPlan);if($('whiteNav'))$('whiteNav').classList.toggle('hidden',!features.white_label)}
async function loadMe(){try{currentUser=await request('/auth/me');realFeatures={...(currentUser.features||{})};renderUsage(currentUser.usage||{});applyPlanUI();loadFundingHealth()}catch(e){console.warn(e.message)}}
function exitPreviewMode(){activePreviewPlan=null;if(currentUser&&realFeatures){currentUser.features={...realFeatures}}renderUsage(currentUser.usage||{});applyPlanUI();toast('Preview mode closed')}
function logout(){clearSession();window.location.replace('/signup.html?mode=login&logged_out=1')}
function showUpgrade(feature){const label=FEATURE_LABELS[feature]||'This feature';toast(label+' is not included in your current plan.');showPage('dashboard',navButton('dashboard'))}
function showPage(id,btn){
 localStorage.setItem('mgs_active_page', id || '');
 if(id !== 'apps') localStorage.removeItem('mgs_active_application_id');

 const feature=PAGE_FEATURE[id];
 if(feature&&!featureAllowed(feature)){showUpgrade(feature);return}

 document.querySelectorAll('.page').forEach(p=>p.classList.add('hidden'));
 if($(id)) $(id).classList.remove('hidden');

 document.querySelectorAll('.nav button').forEach(b=>b.classList.remove('active'));
 if(btn)btn.classList.add('active');

 if(id==='dashboard')loadFundingHealth();
 if(id==='client')loadClientProfile();
 if(id==='profiles')loadProfiles();
 if(id==='grants')loadProfiles().then(()=>updateGrantDefaults(true));
 if(id==='proposals')loadProfiles().then(loadProposals);
 if(id==='workflows')loadProfiles().then(loadWorkflows);
 if(id==='apps'){
 const activeApp = Number(localStorage.getItem('mgs_active_application_id') || 0);
 if(activeApp) openApplication(activeApp); else loadApps();
 }
 if(id==='documents')loadDocuments();
 if(id==='admin')loadAdmin();
 if(id==='notifications'){loadNotifications();loadNotificationSettings()}
}
function navButton(page){return document.querySelector('.nav button[data-page="'+page+'"]')}
function dashboardGo(type){if(type==='subscriptions'){window.location.href='/index.html#plans';return}showPage('profiles',navButton('profiles'));if(type==='individual'){$('profileType').value='individual';$('profileName').focus()}else{$('profileType').value='business';$('profileName').focus()}}

async function loadClientProfile(){try{const d=await request('/auth/client-profile');const user=d.user||{};const tenant=d.tenant||{};const sub=d.subscription||{};const usage=d.usage||{};const features=d.features||{};const info=(obj)=>Object.entries(obj).map(([k,v])=>`<div class="info-row"><span>${esc(k.replaceAll('_',' '))}</span><strong>${esc(v??'')}</strong></div>`).join('');$('clientAccount').innerHTML=info({name:user.full_name,email:user.email,role:user.role,account_type:user.account_type,email_verified:user.email_verified?'Yes':'No'});$('clientPlan').innerHTML=info({plan:PLAN_LABELS[d.plan]||d.plan,status:sub.status||'active/trial',payment_status:user.payment_status||'trialing'});$('clientWorkspace').innerHTML=info({workspace:tenant.name,slug:tenant.slug,domain:tenant.domain||'Not set',audience:tenant.audience_mode||'all'});$('clientFeatures').innerHTML=Object.keys(FEATURE_LABELS).filter(k=>k!=='admin').map(k=>`<div class="usage-card ${features[k]?'':'locked'}"><span class="mini">${FEATURE_LABELS[k]}</span><strong>${features[k]?'Included':'Locked'}</strong></div>`).join('');$('clientProfiles').innerHTML=(d.profiles||[]).map(o=>`<div class="item"><span class="pill">${esc(o.profile_type||o.org_type||'profile')}</span><h3>${esc(o.name)}</h3><p>${esc(o.city||'')} ${esc(o.state||'')}</p><p>${esc(o.funding_goals||o.mission||'')}</p></div>`).join('')||'<p class="muted">No funding profiles yet.</p>'}catch(e){toast(e.message)}}
async function createProfile(){const pt=$('profileType').value;const body={name:$('profileName').value||'My Funding Profile',profile_type:pt,org_type:pt,state:$('profileState').value,city:$('profileCity').value,annual_income:$('profileIncome').value?Number($('profileIncome').value):null,annual_budget:$('profileIncome').value?Number($('profileIncome').value):null,education_level:$('profileEducation').value,mission:$('profileGoals').value,funding_goals:$('profileGoals').value,veteran_status:$('veteranStatus').checked,disability_status:$('disabilityStatus').checked,eligibility_tags:[pt,$('profileEducation').value].filter(Boolean)};await request('/organizations',{method:'POST',body:JSON.stringify(body)});toast('Funding profile created');loadProfiles()}
async function loadProfiles(){profiles=await request('/organizations');$('profileList').innerHTML=profiles.map(o=>`<div class="item"><span class="pill">${esc(o.profile_type||o.org_type||'profile')}</span><h3>${esc(o.name)}</h3><p>${esc(o.city||'')} ${esc(o.state||'')}</p><p>${esc(o.funding_goals||o.mission||'')}</p></div>`).join('')||'<p class="muted">No funding profiles yet.</p>';const opts=profiles.map(o=>`<option value="${o.id}">${esc(o.name)} - ${esc(o.profile_type||o.org_type)}</option>`).join('');const oldGrant=$('grantProfile')?.value||'';if($('grantProfile')){$('grantProfile').innerHTML='<option value="">No profile selected</option>'+opts;if(oldGrant){$('grantProfile').value=oldGrant}else if(profiles.length){$('grantProfile').value=String(profiles[0].id)}}$('proposalProfile').innerHTML=opts||'<option value="">Create a funding profile first</option>';$('workflowProfile').innerHTML=opts||'<option value="">Create a funding profile first</option>';if($('documentProfile'))$('documentProfile').innerHTML='<option value="">General documents</option>'+opts;updateProposalDefaults();updateGrantDefaults(false)}
function selectedProfile(){const id=Number($('proposalProfile')?.value||0);return profiles.find(p=>Number(p.id)===id)||null}
function parseMoney(text){const m=String(text||'').match(/\$?\s*([0-9][0-9,]{2,})(?:\s*(k|K))?/);if(!m)return null;let n=Number(m[1].replace(/,/g,''));if(m[2])n*=1000;return n>0?n:null}
function estimateRequestAmount(profile){if(!profile)return '';const direct=parseMoney(profile.funding_goals)||parseMoney(profile.mission);if(direct)return Math.round(direct);const base=Number(profile.annual_budget||profile.annual_income||0);if(base>0){return Math.round(Math.max(5000,Math.min(100000,base*0.1)))}return ''}
function profileFundingPurpose(profile){if(!profile)return '';const parts=[];if(profile.funding_goals)parts.push(profile.funding_goals);else if(profile.mission)parts.push(profile.mission);if(profile.profile_type||profile.org_type)parts.push(`Applicant type: ${profile.profile_type||profile.org_type}.`);if(profile.city||profile.state)parts.push(`Location: ${[profile.city,profile.state].filter(Boolean).join(', ')}.`);if(profile.veteran_status)parts.push('Veteran-related eligibility should be considered.');if(profile.disability_status)parts.push('Disability-related need should be considered.');return parts.join('\n')}
function updateProposalDefaults(force=false){if(!$('proposalProfile'))return;const p=selectedProfile();const amount=$('amount');const purpose=$('purpose');if(!p){if($('proposalAutoSummary'))$('proposalAutoSummary').innerHTML='<span class="mini">Choose a funding profile to auto-fill amount and purpose.</span>';return}const suggested=estimateRequestAmount(p);const purposeText=profileFundingPurpose(p);if(amount && (force||!amount.value||amount.dataset.autofilled==='1')){amount.value=suggested||'';amount.dataset.autofilled=suggested?'1':'0'}if(purpose && (force||!purpose.value||purpose.dataset.autofilled==='1')){purpose.value=purposeText;purpose.dataset.autofilled=purposeText?'1':'0'}if($('proposalAutoSummary')){$('proposalAutoSummary').innerHTML=`<strong>Auto-filled from ${esc(p.name)}</strong><br><span class="mini">Requested amount and purpose are based on the selected funding profile. You can edit them before generating.</span>`}}
function markProposalManual(){if($('amount'))$('amount').dataset.autofilled='0';if($('purpose'))$('purpose').dataset.autofilled='0'}

function selectedGrantProfile(){const id=Number($('grantProfile')?.value||0);return profiles.find(p=>Number(p.id)===id)||null}
function grantKeywordsFromProfile(p){if(!p)return '';const type=(p.profile_type||p.org_type||'').toLowerCase();const goals=(p.funding_goals||p.mission||'').toLowerCase();const bits=[];if(p.name)bits.push(p.name);if(type)bits.push(type);if(goals)bits.push(p.funding_goals||p.mission);if(type.includes('startup')||goals.includes('startup'))bits.push('startup founder funding');if(type.includes('business')||goals.includes('business')||goals.includes('cafe')||goals.includes('coffee'))bits.push('small business equipment expansion');if(type.includes('nonprofit'))bits.push('nonprofit program support');if(type.includes('student'))bits.push('student tuition scholarship');if(p.veteran_status)bits.push('veteran');if(p.disability_status)bits.push('disability assistance');return [...new Set(bits.filter(Boolean))].join(' ')}
function updateGrantDefaults(force=false){if(!$('grantProfile'))return;const p=selectedGrantProfile();if(!p){if($('grantProfileSummary'))$('grantProfileSummary').innerHTML='Select a funding profile and Mogul Grant System will auto-fill the search focus, audience, category, and state.';return}const q=grantKeywordsFromProfile(p);const type=String(p.profile_type||p.org_type||'').toLowerCase();if($('grantQuery')&&(force||!$('grantQuery').value||$('grantQuery').dataset.autofilled==='1')){$('grantQuery').value=q;$('grantQuery').dataset.autofilled='1'}if($('grantState')&&p.state)$('grantState').value=p.state;if($('grantAudience')){$('grantAudience').value=['individual','student','artist','veteran','family','homeowner'].includes(type)?'individual':'organization'}if($('grantCategory')){if(type.includes('startup'))$('grantCategory').value='startup';else if(type.includes('business'))$('grantCategory').value='business';else if(type.includes('student'))$('grantCategory').value='education';else if(type.includes('homeowner')||type.includes('family'))$('grantCategory').value='benefits';else if(type.includes('nonprofit'))$('grantCategory').value='private';}
if($('grantProfileSummary')){$('grantProfileSummary').innerHTML=`<strong>Searching for ${esc(p.name)}</strong><br><span class="mini">Search focus, audience, category, and state were filled from this funding profile. You can edit before searching.</span>`}}
function markGrantManual(){if($('grantQuery'))$('grantQuery').dataset.autofilled='0'}

async function searchGrants(){try{$('grantResults').innerHTML='<p class=\"muted\">Searching verified grants only...</p>';const body={query:$('grantQuery').value||'funding assistance',state:$('grantState').value||null,organization_id:$('grantProfile').value?Number($('grantProfile').value):null,audience:$('grantAudience').value,category:$('grantCategory').value,limit:12};const d=await request('/grants/search',{method:'POST',body:JSON.stringify(body)});const grants=d.grants||[];if(!grants.length){$('grantResults').innerHTML=`<div class=\"item\"><h3>No verified relevant grants found yet</h3><p>${esc(d.message||'No matching verified grants were found for this state and need. No dummy grants are shown.')}</p><p class=\"muted\">Tip: broaden the need, select All USA, or add/run verified sources for that state. No dummy grants are shown.</p></div>`;return;}$('grantResults').innerHTML=grants.map(g=>`<div class=\"item\"><span class=\"pill\">ID ${g.id} • ${esc(g.audience)} • Match ${Math.round(g.match_score||g.confidence_score||0)}%</span><h3>${esc(g.title)}</h3><p>${esc(g.description)}</p><p class=\"muted\">Category: ${esc(g.category||'')} • State: ${esc(g.state||'National')} • Source: ${esc(g.source)} • Deadline: ${esc(g.deadline||'Varies')}</p><div class=\"actions\"><a class=\"btn secondary\" href=\"${g.application_url||'#'}\" target=\"_blank\">Official Link</a><button type=\"button\" class=\"btn secondary\" onclick=\"useGrant(${Number(g.id)||0})\">Use This Grant</button></div></div>`).join('')}catch(e){$('grantResults').innerHTML='<p class=\"muted\">Search error: '+esc(e.message)+'</p>'}}
async function useGrant(id){
 id = Number(id || 0);
 if(!id){ toast('Please select a valid funding opportunity.'); return; }

 try{
 if($('proposalGrantId')) $('proposalGrantId').value = id;
 if($('workflowGrantId')) $('workflowGrantId').value = id;

 const profileId = $('grantProfile') && $('grantProfile').value
 ? Number($('grantProfile').value)
 : (profiles && profiles[0] ? Number(profiles[0].id) : 0);

 if(!profileId){
 toast('Create or select an organization profile first.');
 showPage('profiles', navButton('profiles'));
 return;
 }

 const created = await request('/applications', {
 method:'POST',
 body:JSON.stringify({
 organization_id: profileId,
 grant_id: id,
 proposal_id: null,
 notes: 'Application page created from selected funding opportunity.'
 })
 });

 const appId = Number(created.id || created.application_id || 0);
 if(!appId) throw new Error('Application was created but no ID was returned.');
 toast('Application page created.');
 await openApplication(appId);
 }catch(e){
 toast(e.message || 'Could not create the application page. Opening proposal studio instead.');
 if($('proposalGrantId')) $('proposalGrantId').value = id;
 if($('workflowGrantId')) $('workflowGrantId').value = id;
 showPage('proposals', navButton('proposals'));
 }
}
async function generateProposal(){try{if(!featureAllowed('proposals'))return showUpgrade('proposals');if(!$('proposalProfile').value){toast('Create or select a funding profile first.');showPage('profiles',navButton('profiles'));return}updateProposalDefaults(false);const d=await request('/proposals/generate',{method:'POST',body:JSON.stringify({organization_id:Number($('proposalProfile').value),grant_id:$('proposalGrantId').value?Number($('proposalGrantId').value):null,requested_amount:$('amount').value?Number($('amount').value):null,funding_purpose:$('purpose').value})});toast('Application narrative generated. Score '+Math.round(d.score||0));loadProposals();if(d.application_id){openApplication(d.application_id)}}catch(e){toast(e.message)}}
async function downloadProposal(id){try{const res=await fetch(api+'/proposals/'+id+'/pdf',{headers:{Authorization:'Bearer '+token}});if(!res.ok){let msg='PDF download failed';try{const j=await res.json();msg=j.detail||msg}catch(_){ }throw new Error(msg)}const blob=await res.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='application-narrative-'+id+'.pdf';document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);toast('PDF downloaded')}catch(e){toast(e.message)}}
async function loadProposals(){const arr=await request('/proposals');$('proposalList').innerHTML=(arr||[]).map(p=>`<div class=\"item\"><span class=\"pill\">Score ${Math.round(p.score||0)}</span><h3>${esc(p.title)}</h3><p class=\"muted\">${esc(p.created_at||'')}</p><button type=\"button\" class=\"btn secondary\" onclick=\"downloadProposal(${p.id})\">Download PDF</button></div>`).join('')||'<p class=\"muted\">No application narratives yet.</p>'}
async function startWorkflow(){try{if(!featureAllowed('workflows'))return showUpgrade('workflows');if(!$('workflowProfile').value){toast('Create or select a funding profile first.');showPage('profiles',navButton('profiles'));return}const payload={workflow:'full_grant_pipeline',organization_id:Number($('workflowProfile').value)};if($('workflowGrantId').value){payload.grant_id=Number($('workflowGrantId').value)}const d=await request('/workflows/start',{method:'POST',body:JSON.stringify(payload)});activeWorkflowId=d.id||d.workflow_run_id||null;renderPipelineStepper(['queued']);$('workflowOut').innerHTML=renderPipelineSummary({id:activeWorkflowId,status:'queued',result_json:{next_action:'Agents are starting. Grant Hunter will select a verified opportunity if Grant ID is blank.'},organization_id:payload.organization_id,grant_id:payload.grant_id});$('workflowArtifacts').innerHTML='';toast('AI agents started.');setTimeout(loadWorkflows,1800);setTimeout(loadAgentRuns,2500)}catch(e){$('workflowOut').innerHTML='<p class="muted">'+esc(e.message)+'</p>'}}
async function loadWorkflows(){try{const runs=await request('/workflows');const arr=Array.isArray(runs)?runs:(runs.workflows||[]);const latest=arr[0];if(!latest){activeWorkflowId=null;activeWorkflowReady=false;renderPipelineStepper([]);$('workflowOut').innerHTML='<div class="workflow-focus"><span class="pill">Start here</span><h2>No package prepared yet.</h2><p class="muted">Choose a funding profile, then prepare one clean application package.</p></div>';$('workflowArtifacts').innerHTML='';$('agentRuns').innerHTML='<p class="muted">Progress will appear after you prepare a package.</p>';return}activeWorkflowId=activeWorkflowId||latest.id;const selected=arr.find(x=>x.id===activeWorkflowId)||latest;activeWorkflowId=selected.id;const status=(selected.result_json&&selected.result_json.status)||selected.status||'';activeWorkflowReady=Boolean((selected.result_json&&selected.result_json.application_id)||status==='completed'||status==='ready_for_client_approval');renderPipelineStepper(workflowStages(selected));$('workflowOut').innerHTML=renderPipelineSummary(selected);$('workflowArtifacts').innerHTML=renderWorkflowArtifacts(selected);if($('workflowNextActions'))$('workflowNextActions').innerHTML='';await loadAgentRuns()}catch(e){$('workflowOut').innerHTML='<p class="muted">'+esc(e.message)+'</p>'}}
async function loadAgentRuns(){
 try{
 if(activeWorkflowReady){
 $('agentRuns').innerHTML='<div class="item"><span class="pill">Complete</span><h3>Application package is ready.</h3><p class="muted">No more preparation steps are required here. Open the Approval Center to review, approve, and track submission.</p><button type="button" class="btn secondary" data-action="open-current-application">Open Approval Center</button></div>';
 return;
 }
 const path=activeWorkflowId?('/agents/runs?workflow_id='+encodeURIComponent(activeWorkflowId)):'/agents/runs';
 const rows=await request(path);const byAgent=new Map();
 for(const r of rows){if(!byAgent.has(r.agent_name))byAgent.set(r.agent_name,r)}
 const order=['grant_hunter','eligibility','proposal_writer','compliance','reviewer','submission_planner','deadline_monitor'];
 const unique=[...byAgent.values()].filter(r=>order.includes(r.agent_name)).sort((a,b)=>order.indexOf(a.agent_name)-order.indexOf(b.agent_name));
 $('agentRuns').innerHTML=unique.length?unique.slice(0,3).map(renderAgentCard).join(''):'<p class="muted">Progress updates will appear after a workflow runs.</p>';
 }catch(e){$('agentRuns').innerHTML='<p class="muted">Progress updates will appear after a workflow runs.</p>'}
}
async function loadApps(){
 try{
 const arr=await request('/applications');
 $('appDetail').innerHTML='';
 const rows=arr||[];
 $('appList').innerHTML=rows.length?rows.map(a=>renderApplicationCard(a)).join(''):'<div class="item"><h3>No applications yet</h3><p class="muted">Run Funding Workflow or generate a proposal to create your first application package.</p></div>';
 }catch(e){$('appList').innerHTML='<p class="muted">'+esc(e.message||'Could not load applications')+'</p>'}
}
function applicationStatusLabel(status){
 const map={draft:'Needs Review',ready_for_client_approval:'Ready for Approval',approved_ready_to_submit:'Approved — Ready to Submit',submitted:'Submitted',under_review:'Under Review',awarded:'Awarded',rejected:'Not Awarded'};
 return map[status]||String(status||'Needs Review').replaceAll('_',' ')
}
function renderApplicationCard(a){
 const grant=a.grant||{};const proposal=a.proposal||{};const status=applicationStatusLabel(a.status);
 const submitted=a.status==='submitted';const approved=a.status==='approved_ready_to_submit';
 const headline=submitted?'Submitted to funder':approved?'Ready to submit on official site':'Review package before submission';
 return `<div class="item application-row"><span class="pill">${esc(status)}</span><h3>${esc(grant.title||('Application #'+a.id))}</h3><p class="muted">${esc(proposal.title||'Application package prepared')}</p><p>${esc(headline)}</p><div class="actions"><button type="button" class="btn" data-action="open-application" data-id="${a.id}">Open Application</button>${!submitted?`<button type="button" class="btn secondary" data-action="approve-application" data-id="${a.id}">${approved?'Re-check Package':'Approve Package'}</button>`:''}${approved?`<button type="button" class="btn secondary" data-action="submit-application" data-id="${a.id}">Mark Submitted</button>`:''}</div></div>`
}
async function documentsReadyForApplication(app){
 try{
 const docs = await request('/documents');
 const arr = Array.isArray(docs) ? docs : [];
 if(!arr.length) return false;

 const orgId = Number(app.organization_id || app.profile_id || (app.organization && app.organization.id) || 0);
 if(!orgId) return arr.length > 0;

 return arr.some(d => {
 const docOrg = Number(d.organization_id || d.profile_id || d.funding_profile_id || (d.organization && d.organization.id) || 0);
 return !docOrg || docOrg === orgId;
 });
 }catch(e){
 return false;
 }
}
async function openApplication(id){
 id = Number(id || localStorage.getItem('mgs_active_application_id') || 0);
 if(!id){ toast('No application selected yet.'); return; }
 localStorage.setItem('mgs_active_application_id', String(id));
 localStorage.setItem('mgs_active_page', 'apps');

 try{
 const a = await request('/applications/' + id);
 localStorage.setItem('mgs_active_application_id', String(a.id || id));
 a.documents_ready = await documentsReadyForApplication(a);

 document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
 if($('apps')) $('apps').classList.remove('hidden');

 document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
 const appNav = navButton('apps');
 if(appNav) appNav.classList.add('active');

 if($('appList')) $('appList').innerHTML = '';
 if($('appDetail')){
 $('appDetail').innerHTML = renderApplicationDetail(a);
 setTimeout(() => $('appDetail').scrollIntoView({behavior:'smooth', block:'start'}), 40);
 }
 }catch(e){
 toast(e.message || 'Could not open application');
 }
}
function renderChecklistItem(label,ready,detail=''){
 return `<div class="review-line ${ready?'ready':'needs'}"><span>${esc(label)}</span><strong>${ready?'Ready':'Needs review'}</strong></div>${detail?`<p class="mini">${esc(detail)}</p>`:''}`
}
function normalizeFundingApplyUrl(grant){
 const raw = grant && (
 grant.apply_url ||
 grant.application_url ||
 grant.external_url ||
 grant.link ||
 grant.url
 );

 if(raw && /^https?:\/\//i.test(raw)){
 return raw;
 }

 return 'https://ambergrantsforwomen.com/get-an-amber-grant/apply-now/';
}

function renderApplicationDetail(a){
 const externalApplyUrl = normalizeFundingApplyUrl(a.grant || a);
 const grant=a.grant||{};const proposal=a.proposal||{};const org=a.organization||{};const status=applicationStatusLabel(a.status);const official=grant.application_url||'#';
 const approved=a.status==='approved_ready_to_submit';const submitted=a.status==='submitted';
 const next=submitted?'You marked this as submitted. Track the funder response and reporting dates next.':approved?'Open the official funder website, submit externally, then mark this as submitted here.':'Review the proposal, confirm attachments, then approve this package when ready.';
 return `<div class="application-detail card"><button type="button" class="btn secondary small" data-action="load-apps">Back to applications</button><span class="pill">${esc(status)}</span><h2>${esc(grant.title||'Application Package')}</h2><p class="muted">Profile: ${esc(org.name||'Selected profile')} • Proposal: ${esc(proposal.title||'Draft not attached')}</p><div class="simple-step-row"><div class="step done"><strong>1. Draft</strong><span>Prepared</span></div><div class="step done"><strong>2. Review</strong><span>Checklist ready</span></div><div class="step ${approved||submitted?'done':'active'}"><strong>3. Approval</strong><span>${approved||submitted?'Approved':'Your action'}</span></div><div class="step ${submitted?'done':'waiting'}"><strong>4. Submit</strong><span>On official site</span></div></div><div class="approval-grid"><div class="item"><h3>Package Checklist</h3>${renderChecklistItem('Proposal draft',!!proposal.id)}${renderChecklistItem('Budget estimate',true)}${renderChecklistItem('Supporting documents',!!a.documents_ready,a.documents_ready?'Documents uploaded for this organization.':'Upload required attachments before submitting externally.')}</div><div class="item"><h3>What to do next</h3><p>${esc(next)}</p><div class="actions">${proposal.id?`<button type="button" class="btn secondary" data-action="download-proposal" data-id="${proposal.id}">Download Proposal PDF</button>`:''}${!approved&&!submitted?`<button type="button" class="btn" data-action="approve-application" data-id="${a.id}">Approve Package</button>`:''}${approved?`<button type="button" class="btn" data-action="submit-application" data-id="${a.id}">Mark Submitted</button>`:''}</div></div><div class="item"><h3>Official Application</h3><p class="muted">Final submission happens on the funder's official website.</p><a class="btn secondary" href="${esc(official)}" target="_blank" rel="noopener">Apply Now</a></div></div></div>`
}
async function approveApp(id){
 try{
 await request('/applications/'+id+'/approve',{method:'POST'});
 toast('Package approved. Next: submit on the official funder website.');
 await openApplication(id);
 await loadMe();
 }catch(e){toast(e.message||'Approval failed')}
}
async function submitApp(id){
 try{
 await request('/applications/'+id+'/mark-submitted',{method:'POST'});
 toast('Marked submitted. Mogul Grant System will keep this in your tracker.');
 await openApplication(id);
 await loadMe();
 }catch(e){toast(e.message||'Could not mark submitted')}
}

async function uploadDocument(){try{if(!featureAllowed('documents'))return showUpgrade('documents');const f=$('documentFile').files[0];if(!f){toast('Choose a file first');return}const fd=new FormData();fd.append('file',f);if($('documentProfile').value)fd.append('organization_id',$('documentProfile').value);fd.append('document_type',$('documentType').value||'supporting_document');const r=await fetch(api+'/documents',{method:'POST',headers:{Authorization:'Bearer '+token},body:fd});const text=await r.text();let d={};try{d=text?JSON.parse(text):{}}catch(_){d={detail:text}}if(!r.ok)throw new Error(d.detail||text||'Upload failed');toast('Document uploaded');$('documentFile').value='';loadDocuments();loadMe()}catch(e){toast(e.message)}}
async function loadDocuments(){try{const arr=await request('/documents');$('documentList').innerHTML=(arr||[]).map(renderDocumentCard).join('')||'<p class="muted">No documents uploaded yet.</p>'}catch(e){$('documentList').innerHTML='<p class="muted">'+esc(e.message)+'</p>'}}
function documentReview(d){const name=String(d.original_filename||'').toLowerCase();const type=String(d.document_type||'').toLowerCase();const content=String(d.content_type||'').toLowerCase();const readable=content.includes('pdf')||content.includes('text')||content.includes('word')||name.endsWith('.pdf')||name.endsWith('.doc')||name.endsWith('.docx')||name.endsWith('.txt');const important=/(budget|ein|501|tax|business|plan|resume|transcript|proposal|irs|certification|letter)/.test(name+' '+type);const missing=[];if(!important)missing.push('Label this file as budget, EIN, business plan, resume, transcript, or certification if applicable');if(!readable)missing.push('Upload PDF, Word, or text format when possible so Mogul Grant System can read it better');return {status:readable?'Accepted':'Needs review',readability:readable?'Readable':'May be hard to read',usefulness:important?'High':'Medium',missing};}
function renderDocumentCard(d){const r=documentReview(d);return `<div class="item"><span class="pill">${esc(r.status)} • ${Math.round((d.size_bytes||0)/1024)} KB</span><h3>${esc(d.original_filename)}</h3><div class="profile-info"><div class="info-row"><span>Document type</span><strong>${esc(d.document_type||'Supporting file')}</strong></div><div class="info-row"><span>Readability</span><strong>${esc(r.readability)}</strong></div><div class="info-row"><span>Funding usefulness</span><strong>${esc(r.usefulness)}</strong></div></div>${r.missing.length?`<div class="upgrade-box"><strong>Needs review</strong><br>${r.missing.map(x=>'• '+esc(x)).join('<br>')}</div>`:`<p class="muted">This file looks ready to support proposals and eligibility checks.</p>`}<a class="btn secondary" href="${api}/documents/${d.id}/download" target="_blank" onclick="event.preventDefault();downloadDocument(${d.id},'${esc(d.original_filename)}')">Download</a></div>`}

async function downloadDocument(id,name){try{const res=await fetch(api+'/documents/'+id+'/download',{headers:{Authorization:'Bearer '+token}});if(!res.ok)throw new Error('Download failed');const blob=await res.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name||'document';document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url)}catch(e){toast(e.message)}}

async function loadNotifications(){try{if($('notificationList'))$('notificationList').innerHTML='<p class="muted">Refreshing alerts...</p>';await loadNotificationSettings();const d=await request('/notifications');const unread=d.unread||0;$('notifBadge').textContent=unread;$('notifBadge').classList.toggle('hidden',!unread);const rows=d.notifications||[];$('notificationList').innerHTML=rows.map(renderNotificationCard).join('')||'<p class="muted">No notifications yet. Run a scan to create grant alerts.</p>';renderNotificationActions(rows)}catch(e){if($('notificationList'))$('notificationList').innerHTML='<p class="muted">'+esc(e.message)+'</p>'}}
function renderNotificationCard(n){const read=n.is_read?'Read':'Unread';const action=n.action_url?`<a class="btn secondary" href="${esc(n.action_url)}" target="_blank">Official Link</a>`:'';const button=n.is_read?'<span class="pill">Already read</span>':`<button type="button" class="btn" onclick="markNotificationRead(${n.id})">Mark Read</button>`;return `<div class="item"><span class="pill">${esc(read)} • ${esc(n.priority||'normal')}</span><h3>${esc(n.title||'Grant alert')}</h3><p>${esc(n.message||'A relevant funding update is available.')}</p><div class="actions">${action}${button}</div></div>`}
function renderNotificationActions(rows){if(!$('notificationNextActions'))return;const unread=(rows||[]).filter(n=>!n.is_read);const read=(rows||[]).filter(n=>n.is_read);if(unread.length){$('notificationNextActions').innerHTML=`<div class="action-card"><h4>${unread.length} alert${unread.length>1?'s':''} need review</h4><p class="muted">Open the official link, verify eligibility, then move promising opportunities into the pipeline.</p></div>`;return}if(read.length){$('notificationNextActions').innerHTML=`<div class="action-card"><h4>Next Recommended Action</h4><p class="muted">You read the latest alerts. Create or update a funding profile, then run Opportunity Radar to find the strongest next match.</p><button type="button" class="btn secondary" onclick="showPage('grants',navButton('grants'))">Open Opportunity Radar</button></div>`;return}$('notificationNextActions').innerHTML=`<div class="action-card"><h4>No alerts yet</h4><p class="muted">Run a scan after creating a funding profile to generate personalized grant alerts.</p></div>`}
async function markNotificationRead(id){await request('/notifications/'+id+'/read',{method:'POST'});toast('Alert marked read. Next action updated.');await loadNotifications()}
async function scanNotifications(){const d=await request('/notifications/scan-now',{method:'POST'});toast('Created '+(d.created_notifications||0)+' new grant alerts');await loadNotifications()}
async function loadNotificationSettings(){try{const s=await request('/notifications/settings');$('emailGrantMatches').checked=!!s.email_grant_matches;$('platformGrantMatches').checked=!!s.platform_grant_matches;$('minimumMatchScore').value=s.minimum_match_score||75}catch(e){}}
async function saveNotificationSettings(){await request('/notifications/settings',{method:'PATCH',body:JSON.stringify({email_grant_matches:$('emailGrantMatches').checked,platform_grant_matches:$('platformGrantMatches').checked,email_deadline_reminders:true,minimum_match_score:Number($('minimumMatchScore').value||75),categories_json:[],states_json:[]})});toast('Notification settings saved')}

function renderKeyValues(obj){return '<div class="kv-grid">'+Object.entries(obj||{}).map(([k,v])=>`<div class="kv"><span>${esc(k.replaceAll('_',' '))}</span><strong>${esc(v===true?'Yes':v===false?'No':v??'')}</strong></div>`).join('')+'</div>'}
function renderAdminDashboard(d){const counts={tenants:d.tenants,users:d.users,grants:d.grants,proposals:d.proposals,applications:d.applications,workflows:d.workflows,agent_runs:d.agent_runs,documents:d.documents,usage_events:d.usage_events,audit_logs:d.audit_logs};let html='<h3>Platform Overview</h3>'+renderKeyValues(counts);if(d.current_user_usage){const u=d.current_user_usage;html+=`<h3 style="margin-top:18px">Current Admin Plan</h3>`+renderKeyValues({plan:u.label||u.plan,credits_remaining:u.credits?.remaining>=999999?'Unlimited':u.credits?.remaining,grant_searches_used:u.used?.grant_searches||0,proposals_used:u.used?.proposals||0,workflows_used:u.used?.workflows||0,reset_date:u.credits?.reset_date||'monthly'});}return html}
function prettyAgentName(name){return String(name||'agent').replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase())}
function normalizeValue(v){if(v===null||v===undefined||v==='')return 'Not available';if(Array.isArray(v)){return v.map(x=>typeof x==='object'?(x.title||x.name||x.label||x.website||'matched item'):x).filter(Boolean).slice(0,5).join(', ')||'Not available'}if(typeof v==='object'){return v.title||v.name||v.label||v.status||v.message||Object.entries(v).slice(0,3).map(([k,val])=>`${humanKey(k)}: ${normalizeValue(val)}`).join(' • ')}if(typeof v==='boolean')return v?'Yes':'No';return String(v)}
function humanKey(k){return String(k||'').replaceAll('_',' ').replace(/\b\w/g,m=>m.toUpperCase())}
function workflowStages(w){const result=w?.result_json||{};const status=w?.status||'';const completed=status==='completed'||result.status==='ready_for_client_approval';if(status==='queued')return ['queued'];if(status==='running')return ['grant_hunter','eligibility'];if(completed)return ['grant_hunter','eligibility','proposal_writer','compliance','submission_planner'];if(status==='failed')return ['failed'];return []}
function renderPipelineStepper(done){
 const steps=[['grant_hunter','1. Find funding','Matched opportunity'],['eligibility','2. Check fit','Eligibility reviewed'],['proposal_writer','3. Draft package','Proposal prepared'],['compliance','4. Review items','Checklist created'],['submission_planner','5. Ready for approval','You review next']];
 if(!$('pipelineStepper'))return;const set=new Set(done||[]);const complete=set.has('submission_planner')||set.has('completed');
 $('pipelineStepper').innerHTML=steps.map(([key,title,sub],idx)=>`<div class="step ${complete||set.has(key)?'done':(idx===0?'active':'waiting')}"><strong>${esc(title)}</strong><span>${esc(sub)}</span></div>`).join('')
}
function renderPipelineSummary(w){
 const r=w?.result_json||{};const status=r.status||w?.status||'in progress';
 const grant=r.grant_title||r.selected_title||r.title||'Funding match in progress';
 const score=r.match_score||r.score||'Pending';
 const ready=Boolean(r.application_id||status==='completed'||status==='ready_for_client_approval');
 if(!ready){return `<div class="workflow-focus"><span class="pill">Preparing package</span><h2>Mogul Grant System is building your application package.</h2><p class="muted">This usually creates a shortlist, checks fit, drafts the proposal, and prepares the approval checklist.</p></div>`}
 return `<div class="workflow-focus success"><span class="pill">Ready for your review</span><h2>${esc(grant)}</h2><p>Mogul Grant System prepared the draft and checklist. Your only required next step is to review the application package before anything is submitted.</p><div class="summary-card clean-summary"><div class="summary-metric"><span>Status</span><strong>Ready for review</strong></div><div class="summary-metric"><span>Match score</span><strong>${esc(score)}%</strong></div><div class="summary-metric"><span>Submission safety</span><strong>Your approval required</strong></div></div>${renderWorkflowNextActions(w)}</div>`
}
function renderWorkflowNextActions(w){
 const r=w?.result_json||{};
 if(r.application_id){
 return `<div class="next-actions single-next"><h3>Next step</h3><div class="action-card primary-next"><h4>Review application package</h4><p class="muted">Open the Approval Center, review the proposal and checklist, then approve only when everything is correct.</p><button type="button" class="btn" data-action="open-application" data-id="${Number(r.application_id)}">Open Approval Center</button></div></div>`
 }
 if(r.proposal_id){
 return `<div class="next-actions single-next"><h3>Next step</h3><div class="action-card primary-next"><h4>Review proposal draft</h4><p class="muted">Open Proposal Studio and review the generated narrative.</p><button type="button" class="btn" data-action="go-page" data-page="proposals">Open Proposal Studio</button></div></div>`
 }
 return `<div class="next-actions single-next"><h3>Next step</h3><div class="action-card primary-next"><h4>Create a stronger funding profile</h4><p class="muted">Add goals, location, budget, and documents so Mogul Grant System can prepare better matches.</p><button type="button" class="btn" data-action="go-page" data-page="profiles">Open Funding Profiles</button></div></div>`
}
function renderWorkflowArtifacts(w){
 const r=w?.result_json||{};const items=[];
 if(r.application_id)items.push(['Approval Center','Ready for review','Open',`app:${r.application_id}`]);
 else if(r.proposal_id)items.push(['Proposal Studio','Draft ready','Open','proposals']);
 if(r.official_application_url)items.push(['Official source','Verify before applying','Open',r.official_application_url]);
 if(r.deadline)items.push(['Deadline',r.deadline,'Track','apps']);
 return items.map(([title,meta,cta,target])=>`<div class="artifact-card compact"><span class="mini">${esc(meta)}</span><h3>${esc(title)}</h3>${String(target).startsWith('http')?`<a class="btn secondary" href="${esc(target)}" target="_blank" rel="noopener">${esc(cta)}</a>`:String(target).startsWith('app:')?`<button type="button" class="btn secondary" onclick="openApplication(${Number(String(target).split(':')[1])})">${esc(cta)}</button>`:`<button type="button" class="btn secondary" onclick="showPage('${esc(target)}',navButton('${esc(target)}'))">${esc(cta)}</button>`}</div>`).join('')
}
function agentMessage(name,out){
 out=out||{};const grant=out.selected_title||out.title||out.grant_title||'a verified opportunity';const score=out.match_score||out.score;
 const maps={
 grant_hunter:{title:'Funding Match Found',body:`Best match: ${grant}${score?` • ${score}% fit`:''}.`},
 eligibility:{title:'Eligibility Reviewed',body:out.eligible_likely===false?'This may need manual review before applying.':'This opportunity appears aligned with the profile.'},
 budget:{title:'Budget Estimate Prepared',body:`Suggested request: ${out.requested_amount_estimate?('$'+Number(out.requested_amount_estimate).toLocaleString()):'confirm amount before submission'}.`},
 compliance:{title:'Checklist Created',body:out.risk_level?`Submission risk: ${out.risk_level}.`:'Review required items before approval.'},
 proposal_writer:{title:'Proposal Draft Ready',body:`Draft quality score: ${score||85}/100.`},
 reviewer:{title:'AI Review Complete',body:`Review score: ${score||85}/100.`},
 submission_planner:{title:'Approval Package Ready',body:'Open the Approval Center to review and approve.'},
 deadline_monitor:{title:'Deadline Tracking Started',body:`Deadline: ${out.deadline||'verify current cycle'}.`}
 };
 return maps[name]||{title:prettyAgentName(name),body:'Step completed.'}
}
function renderAgentCard(a){
 const out=a.output_json||{};const msg=agentMessage(a.agent_name,out);
 return `<div class="human-agent-row"><strong>${esc(msg.title)}</strong><span>${esc(msg.body)}</span></div>`
}
function renderAgentLines(name,out){const msg=agentMessage(name,out||{});return `<div class="human-line">${esc(msg.body)}</div><div class="human-line"><strong>Next:</strong> ${esc(msg.next)}</div>`}
function renderFundingHealth(d){if(!$('fundingHealth'))return;const components=d.components||{};const score=Number(d.score||0);const risks=(d.risks||[]).slice(0,3);const strengths=(d.strengths||[]).slice(0,3);const actions=(d.recommended_actions||[]).slice(0,3);$('fundingHealth').innerHTML=`<div class="health-score" style="--score:${score}"><div><b>${score}</b><br><span>/100</span></div></div><div><h3>${esc(d.label||'Funding Readiness')}</h3><p class="muted">Computed from eligibility, organization readiness, proposal strength, financial stability, compliance, history, and timing.</p><div class="component-grid">${Object.entries(components).map(([k,v])=>`<div class="component"><span>${esc(k.replaceAll('_',' '))}</span><strong>${esc(v)}/100</strong></div>`).join('')}</div><div class="grid" style="grid-template-columns:repeat(3,1fr);margin-top:14px"><div><h3>Strengths</h3><div class="health-list">${(strengths.length?strengths:['Add more profile data to identify strengths']).map(x=>`<div>✓ ${esc(x)}</div>`).join('')}</div></div><div><h3>Risks</h3><div class="health-list">${(risks.length?risks:['No major risk flagged yet']).map(x=>`<div>⚠ ${esc(x)}</div>`).join('')}</div></div><div><h3>Recommended Actions</h3><div class="health-list">${actions.map(x=>`<div>→ ${esc(x)}</div>`).join('')}</div></div></div></div>`}
async function loadFundingHealth(){try{const d=await request('/analytics/funding-health');renderFundingHealth(d)}catch(e){if($('fundingHealth'))$('fundingHealth').innerHTML='<p class="muted">Create a funding profile to calculate your Funding Health Score.</p>'}}
function renderWorkflowCard(w){return renderPipelineSummary(w)}
function renderAgentOutput(output){if(!output||typeof output!=='object')return esc(output||'No details yet.');return '<div class="check-list">'+Object.entries(output).slice(0,8).map(([k,v])=>`<div><strong>${esc(k.replaceAll('_',' '))}:</strong> ${esc(normalizeValue(v))}</div>`).join('')+'</div>'}
function renderTenantSaved(d){return '<h3>Branding saved</h3>'+renderKeyValues({name:d.name,domain:d.domain||'Not set',primary_color:d.primary_color,background_color:d.background_color,audience_mode:d.audience_mode})}
function renderPreviewDetails(plan,features,matrix){let html=`<div class="preview-banner"><strong>Viewing as:</strong> ${esc(PLAN_LABELS[plan]||plan)}<br><span class="mini">Sidebar/features now reflect this plan. This does not change your real admin account.</span><br><br><button type="button" class="btn secondary" onclick="exitPreviewMode()">Exit Preview Mode</button></div>`;const m=(matrix&&matrix[0])||{};html+='<h3>Plan Limits</h3>'+renderKeyValues({price:m.price||'',credits:m.credits>=999999?'Unlimited':m.credits,grant_searches:m.grant_searches>=999999?'Unlimited':m.grant_searches,proposals:m.proposals>=999999?'Unlimited':m.proposals,workflows:m.workflows>=999999?'Unlimited':m.workflows,documents:m.documents>=999999?'Unlimited':m.documents,pdf_exports:m.pdf_exports>=999999?'Unlimited':m.pdf_exports});html+='<h3>Feature Access</h3><div class="usage-grid">'+Object.keys(FEATURE_LABELS).map(k=>`<div class="usage-card ${features[k]?'':'locked'}"><span class="mini">${FEATURE_LABELS[k]}</span><strong>${features[k]?'Included':'Locked'}</strong></div>`).join('')+'</div>';return html}

async function saveTenant(){try{if(!featureAllowed('white_label')){if($('tenantOut'))$('tenantOut').innerHTML='<div class="action-card"><h4>White-label access required</h4><p class="muted">Upgrade to a White Label or Enterprise plan and make sure your user role is Owner or Admin.</p></div>';return showUpgrade('white_label')}const d=await request('/tenants/current',{method:'PATCH',body:JSON.stringify({name:$('tenantName').value,domain:$('tenantDomain').value,primary_color:$('primaryColor').value,background_color:$('bgColor').value,audience_mode:$('audienceMode').value})});$('tenantOut').innerHTML=renderTenantSaved(d);toast('Branding saved')}catch(e){$('tenantOut').innerHTML='<div class="action-card"><h4>White-label setup not available yet</h4><p class="muted">'+esc(e.message)+'</p><p class="muted">Access requires a white-label plan, an admin/owner role, and tenant-level permissions.</p></div>'}}
async function loadAdmin(){loadPlanMatrix();try{const d=await request('/admin/dashboard');$('adminOut').innerHTML=renderAdminDashboard(d)}catch(e){$('adminOut').innerHTML='<p class="muted">Admin overview is unavailable right now.</p>'}}
async function loadPlanMatrix(){const container=$('adminPlanMatrix');if(!container)return;container.innerHTML='<p class="muted">Loading plan matrix...</p>';try{let d;try{d=await request('/admin/plans')}catch(apiErr){d={plans:localPlanMatrix()};toast('Using local plan matrix preview. API plan matrix unavailable.')}const plans=d.plans||[];container.innerHTML=`<div class="admin-grid">${plans.map(renderPlanCard).join('')}</div>`||'<p class="muted">No plans available.</p>'}catch(e){container.innerHTML='<p class="muted">'+esc(e.message)+'</p>'}}
function localPlanMatrix(){return[{plan:'individual_elite',label:'Individual Elite',price:'$99/mo',credits:999999,grant_searches:999999,proposals:999999,workflows:999999,documents:999999,pdf_exports:999999,team_members:1,private_grants:true,white_label:false,admin_access:false,fair_use:true},{plan:'business_owner',label:'Business Owner',price:'$299/mo',credits:999999,grant_searches:999999,proposals:999999,workflows:999999,documents:999999,pdf_exports:999999,team_members:5,private_grants:true,white_label:false,admin_access:false,fair_use:true},{plan:'white_label_platform',label:'White Label Platform',price:'$5,000/yr',credits:999999,grant_searches:999999,proposals:999999,workflows:999999,documents:999999,pdf_exports:999999,team_members:999999,private_grants:true,white_label:true,admin_access:true,fair_use:true}]}
function fmtLimit(v){return Number(v)>=999999?'Unlimited':Number(v||0).toLocaleString()}
function renderPlanCard(p){return `<div class="plan-card-clean"><span class="pill">${esc(p.label)}</span><h3>${esc(p.label)}</h3><div class="price">${esc(p.price||'')}</div><p class="muted">${p.plan==='individual_elite'?'For one serious funding operator.':p.plan==='business_owner'?'For teams and business owners managing funding workflows.':'For agencies deploying their own branded funding platform.'}</p><div class="plan-feature-list"><span>Grant discovery: Included</span><span>Proposal Studio: Included</span><span>Agent Pipeline: Included</span><span>Document Vault and PDF exports: Included</span><span>Team seats: ${fmtLimit(p.team_members)}</span><span>White label: ${p.white_label?'Included':'Not included'}</span></div><button type="button" class="btn secondary" onclick="previewPlan('${esc(p.plan)}')">Preview this plan</button></div>`}
async function previewPlan(plan){try{const d=await request('/admin/preview/'+plan);activePreviewPlan=plan;if(currentUser){currentUser.features=d.features||currentUser.features}applyPlanUI();renderUsage(currentUser?.usage||{});$('adminOut').innerHTML=renderPreviewDetails(plan,d.features||{},d.matrix||[]);showPage('dashboard',navButton('dashboard'));toast('Preview mode active: '+(PLAN_LABELS[plan]||plan))}catch(e){toast(e.message)}}
function esc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#039;','"':'&quot;'}[c]))}
populateStateDropdowns();

async function openCurrentApplication(){
 try{
 const arr=await request('/applications');
 const apps=Array.isArray(arr)?arr:[];
 if(!apps.length){toast('No application package yet. Prepare one first.');showPage('workflows',navButton('workflows'));return;}
 await openApplication(apps[0].id);
 }catch(e){toast(e.message||'Could not open application')}
}
function safePage(page){if(!page)return;showPage(page,navButton(page));}
function setupReliableClicks(){
 document.addEventListener('click', function(e){
 const nav = e.target.closest('.nav button[data-page]');
 if(nav){
 e.preventDefault();
 e.stopPropagation();
 showPage(nav.dataset.page, nav);
 return;
 }

 const el = e.target.closest('[data-action]');
 if(!el) return;

 const action = el.dataset.action;
 const id = Number(el.dataset.id || el.dataset.applicationId || el.dataset.appId || 0);
 const page = el.dataset.page;

 if(action==='go-page'){ e.preventDefault(); e.stopPropagation(); showPage(page, navButton(page)); return; }
 if(action==='load-apps'){ e.preventDefault(); e.stopPropagation(); localStorage.removeItem('mgs_active_application_id'); loadApps(); return; }
 if(action==='open-application' || action==='open-approval' || action==='open-current-application'){
 e.preventDefault(); e.stopPropagation();
 if(id) openApplication(id); else openCurrentApplication();
 return;
 }
 if(action==='open-funding-page' || action==='use-funding-opportunity'){
 e.preventDefault(); e.stopPropagation();
 useGrant(Number(el.dataset.grantId || el.dataset.id || 0));
 return;
 }
 if(action==='approve-application'){ e.preventDefault(); e.stopPropagation(); if(id) approveApp(id); return; }
 if(action==='submit-application'){ e.preventDefault(); e.stopPropagation(); if(id) submitApp(id); return; }
 if(action==='download-proposal'){ e.preventDefault(); e.stopPropagation(); if(id) downloadProposal(id); return; }
 }, true);

 document.querySelectorAll('.nav button[data-page]').forEach(btn=>{
 btn.addEventListener('click',function(e){e.preventDefault();showPage(btn.dataset.page,btn);});
 });
}

$('loginTab').onclick=showLogin;$('signupTab').onclick=showSignup;$('switchToSignup').onclick=showSignup;$('switchToLogin').onclick=showLogin;$('loginButton').onclick=login;$('signupButton').onclick=register;$('logoutButton').onclick=logout;$('createProfileButton').onclick=createProfile;$('searchGrantsButton').onclick=searchGrants;$('generateProposalButton').onclick=generateProposal;if($('grantProfile'))$('grantProfile').onchange=()=>updateGrantDefaults(true);if($('grantQuery'))$('grantQuery').oninput=markGrantManual;if($('proposalProfile'))$('proposalProfile').onchange=()=>updateProposalDefaults(true);if($('amount'))$('amount').oninput=markProposalManual;if($('purpose'))$('purpose').oninput=markProposalManual;$('startWorkflowButton').onclick=startWorkflow;$('loadAppsButton').onclick=loadApps;if($('uploadDocumentButton'))$('uploadDocumentButton').onclick=uploadDocument;$('saveTenantButton').onclick=saveTenant;if($('loadAdminButton'))$('loadAdminButton').onclick=loadAdmin;if($('loadPlanMatrixButton'))$('loadPlanMatrixButton').onclick=loadPlanMatrix;if($('loadNotificationsButton'))$('loadNotificationsButton').onclick=loadNotifications;if($('scanNotificationsButton'))$('scanNotificationsButton').onclick=scanNotifications;if($('saveNotificationSettingsButton'))$('saveNotificationSettingsButton').onclick=saveNotificationSettings;document.querySelectorAll('.nav button').forEach(btn=>btn.onclick=()=>showPage(btn.dataset.page,btn));setupReliableClicks();['loginPassword','signupPassword'].forEach(id=>$(id).addEventListener('keydown',e=>{if(e.key==='Enter') id==='loginPassword'?login():register()}));const params=new URLSearchParams(location.search);const selectedPlan=params.get('plan');const mode=params.get('mode');if(selectedPlan){applySelectedPlan(selectedPlan);showSignup()}else if(mode==='signup'){applySelectedPlan(null);showSignup()}else if(mode==='login'){applySelectedPlan(null);showLogin()}else{applySelectedPlan(null)}if(params.get('payment')==='success'){toast('Payment successful. Your account is active.');history.replaceState({},'',location.pathname)}if(params.get('payment')==='cancelled'){msg('Payment was cancelled.',true);history.replaceState({},'',location.pathname)}if(token)enter();

