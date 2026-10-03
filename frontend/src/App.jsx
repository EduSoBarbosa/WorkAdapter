import { useCallback, useEffect, useRef, useState } from 'react'
import { request, listAll, userPath } from './services/api'
import { Icon, Form, Modal, ErrorBox } from './components/UI'
import Overview from './pages/Overview'
import Profile from './pages/Profile'
import Resumes from './pages/Resumes'
import Applications from './pages/Applications'
import Assistant from './pages/Assistant'
const nav=[['inicio','Visão geral','grid'],['perfil','Meu perfil','user'],['curriculos','Currículos','file'],['vagas','Candidaturas','briefcase'],['assistente','Assistente IA','spark']]
const getPage=()=>nav.some(([k])=>k===location.hash.slice(1))?location.hash.slice(1):'inicio'
function storedUser(){try{return localStorage.getItem('workadapter-user')||''}catch{return ''}}
export default function App(){
  const [page,setPage]=useState(getPage);const [users,setUsers]=useState(null);const [uid,setUid]=useState(storedUser)
  const [data,setData]=useState(null);const [error,setError]=useState('');const [loading,setLoading]=useState(true)
  const [toast,setToast]=useState('');const [newUser,setNewUser]=useState(false);const [retry,setRetry]=useState(0)
  const [aiBusy,setAiBusy]=useState(false)
  const version=useRef(0);const heading=useRef(null)
  useEffect(()=>{const fn=()=>setPage(getPage());window.addEventListener('hashchange',fn);return()=>window.removeEventListener('hashchange',fn)},[])
  useEffect(()=>{if(!toast)return;const t=setTimeout(()=>setToast(''),4500);return()=>clearTimeout(t)},[toast])
  function navigate(next){location.hash=next;setPage(next);heading.current?.focus();window.scrollTo({top:0,behavior:'instant'})}
  useEffect(()=>{const controller=new AbortController();listAll('/usuarios',controller.signal).then(items=>{setUsers(items);setUid(current=>items.some(u=>String(u.id)===current)?current:String(items[0]?.id||''));if(!items.length)setLoading(false);setError('')}).catch(e=>{if(e.name!=='AbortError'){setError(e.message);setLoading(false)}});return()=>controller.abort()},[retry])
  const refresh=useCallback(async()=>{
    if(!uid)return
    const current=++version.current
    setLoading(true)
    try{
      const root=userPath(uid)
      const [profile,cvs,jobs,skills]=await Promise.all([request(`${root}/perfil`),listAll(`${root}/curriculos`),listAll(`${root}/candidaturas`),listAll('/habilidades')])
      if(current!==version.current)return
      setData({profile,cvs,jobs,skills});setUsers(old=>old?.map(u=>u.id===profile.usuario.id?profile.usuario:u));setError('')
    }catch(e){if(current===version.current)setError(e.message)}finally{if(current===version.current)setLoading(false)}
  },[uid])
  useEffect(()=>{if(uid){try{localStorage.setItem('workadapter-user',uid)}catch{/* Armazenamento indisponível: usa estado em memória. */}refresh()}return()=>{version.current++}},[uid,refresh])
  async function createUser(body){const user=await request('/usuarios',{method:'POST',body});setUsers(old=>[...(old||[]),user]);setUid(String(user.id));setNewUser(false);setToast('Perfil criado. Vamos construir sua próxima oportunidade.')}
  const ready=data&&String(data.profile.usuario.id)===uid
  return <><a href="#conteudo" className="skip-link">Pular para o conteúdo</a><div className="app-shell"><aside className="sidebar"><a href="#inicio" className="brand" aria-label="WorkAdapter, início"><span className="brand-mark"><Icon name="layers" size={25}/></span><span>work<span className="brand-light">adapter</span><small>SEU PRÓXIMO CAPÍTULO</small></span></a><div className="nav-caption">WORKSPACE</div><nav aria-label="Navegação principal">{nav.map(([key,label,icon])=><button key={key} aria-label={label} className={`nav-item ${page===key?'active':''}`} onClick={()=>navigate(key)} aria-current={page===key?'page':undefined}><Icon name={icon}/><span>{label}</span>{page===key&&<span className="nav-dot"/>}</button>)}</nav><div className="sidebar-bottom"><div className="local-card"><span className="dot"/><strong>Seu espaço local</strong><p>Construa com intenção.<br/>Avance no seu ritmo.</p></div><span className="version">WORKADAPTER <span>v0.1</span></span></div></aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>{nav.find(([k])=>k===page)?.[1]}</strong></div><div className="topbar-right"><span className={`connection ${error?'offline':''}`}><span className="dot"/>{error?'Sem conexão':loading?'Sincronizando…':'Conectado'}</span>{users?.length>0&&<><label className="sr-only" htmlFor="profile-select">Perfil ativo</label><select id="profile-select" disabled={aiBusy} title={aiBusy?'Aguarde a análise antes de trocar de perfil':undefined} value={uid} onChange={e=>setUid(e.target.value)}>{users.map(u=><option key={u.id} value={u.id}>{u.nome_completo}</option>)}</select><button className="icon-button" aria-label="Criar outro perfil" disabled={aiBusy} onClick={()=>setNewUser(true)}><Icon name="plus"/></button></>}</div></header>
    <main id="conteudo" ref={heading} tabIndex={-1}>{error&&<div className="connection-error"><ErrorBox>{error}</ErrorBox><button className="button secondary" onClick={()=>{setRetry(x=>x+1);refresh()}}>Tentar novamente</button></div>}
    {loading&&!ready?<div className="loading" role="status"><div className="loader"/><h2>Preparando seu workspace</h2><p>Buscando suas informações…</p></div>:users?.length===0?<section className="glass onboarding"><span className="eyebrow">BEM-VINDO AO WORKADAPTER</span><h1>O próximo capítulo<br/>começa com você.</h1><p>Crie seu perfil para reunir experiências, organizar currículos e acompanhar oportunidades.</p><Form fields={[{key:'nome_completo',label:'Seu nome completo',type:'text',required:true},{key:'vaga_alvo_atual',label:'Que vaga você busca?',type:'text'}]} onSubmit={createUser} onCancel={()=>navigate('inicio')} submitLabel="Criar meu perfil"/></section>:ready&&<div key={uid}>{page==='inicio'?<Overview data={data} navigate={navigate}/>:page==='perfil'?<Profile data={data} refresh={refresh} notify={setToast}/>:page==='curriculos'?<Resumes data={data} refresh={refresh} notify={setToast} navigate={navigate}/>:page==='vagas'?<Applications data={data} refresh={refresh} notify={setToast}/>:null}<div hidden={page!=='assistente'}><Assistant data={data} refresh={refresh} notify={setToast} navigate={navigate} onBusy={setAiBusy}/></div></div>}
    <footer className="footer"><span>Feito para o seu próximo passo.</span><span><span className="dot"/> WorkAdapter</span></footer></main></div></div>
    {toast&&<div className="toast" role="status"><Icon name="check"/>{toast}<button className="icon-button" aria-label="Fechar aviso" onClick={()=>setToast('')}><Icon name="close" size={16}/></button></div>}
    {newUser&&<Modal title="Criar outro perfil" onClose={()=>setNewUser(false)}><Form fields={[{key:'nome_completo',label:'Nome completo',type:'text',required:true},{key:'vaga_alvo_atual',label:'Vaga alvo',type:'text'}]} onSubmit={createUser} onCancel={()=>setNewUser(false)}/></Modal>}
  </>
}
