package com.carprice.backend.model;


import com.carprice.backend.service.EmailService;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class UserService {

    private final UserRepository userRepository;
    public UserService(UserRepository userRepository, EmailService emailService) {
        this.userRepository = userRepository;

    }

    public List<User> allUsers(){
        return userRepository.findAll();
    }
}
