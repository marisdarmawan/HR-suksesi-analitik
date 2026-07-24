import pandas as pd

def get_official_category(jabatan, grade=0, company_name=""):
    """
    Mengklasifikasikan level karir pegawai berdasarkan nama jabatan, grade, 
    dan unit kerja (Company Name) sesuai dengan Perdir PT PLN No. 0050/2023.
    """
    j = str(jabatan).lower()
    u = str(company_name).lower()
    
    # Memastikan grade berupa integer yang valid
    grade = int(grade) if pd.notna(grade) else 0
    
    # ==========================================================
    # 1. JALUR STRUKTURAL & GENERALIS TERTENTU
    # ==========================================================
    if 'senior executive' in j or 'kepala satuan' in j or 'senior evp' in j: 
        return 'Manajemen Atas Khusus'
        
    if 'executive vice president' in j or 'general manager' in j or 'evp' in j or 'gm' in j: 
        return 'Manajemen Atas'
        
    if 'vice president' in j or 'senior manager' in j or 'vp' in j: 
        return 'Manajemen Menengah'
        
    if 'manager' in j and not any(x in j for x in ['assistant', 'asman', 'layanan', 'ulp', 'senior', 'general', 'executive', 'vp']):
        return 'Manajemen Dasar'
        
    if 'assistant manager' in j or 'asman' in j: 
        return 'Generalist 3 Tertentu (Asman/Mgr Layanan)'
        
    if 'manager' in j and ('layanan' in u or 'ulp' in u or 'ulp' in j or 'layanan' in j): 
        return 'Generalist 3 Tertentu (Asman/Mgr Layanan)'
        
    if 'team leader' in j: 
        return 'Generalist 2 Tertentu (Team Leader)'
    
    # ==========================================================
    # 2. JALUR FUNGSIONAL SPESIALIS & GENERALIS (FSG)
    # ==========================================================
    if grade >= 18: return 'Senior Specialist'
    if grade >= 15: return 'Specialist'
    if grade >= 13: return 'Generalist 3'
    if grade >= 11: return 'Generalist 2'
    
    return 'Generalist 1'


def is_eligible(curr_cat, curr_grade, tgt_cat):
    """
    Mengevaluasi apakah seorang kandidat memenuhi kualifikasi administratif (eligibility)
    untuk dipromosikan ke posisi target (tgt_cat) berdasarkan level saat ini (curr_cat)
    dan person grade (curr_grade).
    """
    curr_grade = int(curr_grade) if pd.notna(curr_grade) else 0
    
    if tgt_cat == 'Manajemen Atas Khusus':
        if curr_cat in ['Manajemen Atas Khusus', 'Manajemen Atas'] and curr_grade >= 20: 
            return True
        if curr_cat == 'Senior Specialist' and curr_grade >= 20: 
            return True
            
    elif tgt_cat == 'Manajemen Atas':
        if curr_cat in ['Manajemen Atas', 'Manajemen Menengah'] and curr_grade >= 17: 
            return True
        if curr_cat == 'Senior Specialist' and curr_grade >= 18: 
            return True
            
    elif tgt_cat == 'Manajemen Menengah':
        if curr_cat in ['Manajemen Menengah', 'Manajemen Dasar'] and curr_grade >= 14: 
            return True
        if curr_cat in ['Senior Specialist', 'Specialist'] and curr_grade >= 15: 
            return True
            
    elif tgt_cat == 'Manajemen Dasar':
        if curr_cat in ['Manajemen Dasar', 'Generalist 3 Tertentu (Asman/Mgr Layanan)'] and curr_grade >= 12: 
            return True
        if curr_cat in ['Specialist', 'Generalist 3'] and curr_grade >= 13: 
            return True
            
    elif tgt_cat == 'Generalist 3 Tertentu (Asman/Mgr Layanan)':
        if curr_cat in ['Generalist 3 Tertentu (Asman/Mgr Layanan)', 'Generalist 2 Tertentu (Team Leader)'] and curr_grade >= 10: 
            return True
        if curr_cat in ['Generalist 3', 'Generalist 2'] and curr_grade >= 11: 
            return True
            
    elif tgt_cat == 'Generalist 2 Tertentu (Team Leader)':
        if curr_cat == 'Generalist 2 Tertentu (Team Leader)' and curr_grade >= 8: 
            return True
        if curr_cat in ['Generalist 2', 'Generalist 1'] and curr_grade >= 8: 
            return True
            
    return False