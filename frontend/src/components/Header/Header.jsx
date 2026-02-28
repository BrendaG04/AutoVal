import { Link } from 'react-router-dom';
import '../../index.css';

function Header(){
    return(
        <>
        <header className="header">
            <nav className="nav">
                <div className="nav-left">
                    <img className="brand-logo" src='/brenware.png' alt="Brenware Logo" />
                    <Link to='/' className='user-link'>
                        <span className="brand-name">AutoVal</span>
                    </Link>
                </div>
                <div className="nav-right">
                    <Link to='/login' className='user-link'>
                        <span className="header-link">Login</span>
                    </Link>
                    <Link to='/signup' className='user-link'>
                        <span className="header-link">Signup</span>
                    </Link>
                    <Link to='/favorites' className='user-link'>
                        <span className="header-link">Favorites</span>
                    </Link>                
                </div>
            </nav>
        </header>
        </>
    )
}

export default Header;