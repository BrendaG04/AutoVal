package com.carprice.backend.controllers;

import com.carprice.backend.dto.LogInUserDto;
import com.carprice.backend.dto.RegisterUserDto;
import com.carprice.backend.model.User;
import com.carprice.backend.service.AuthenticationService;
import com.carprice.backend.service.JwtService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(AuthenticationController.class)
@AutoConfigureMockMvc(addFilters = false)
class AuthenticationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockitoBean
    private JwtService jwtService;

    @MockitoBean
    private AuthenticationService authenticationService;

    @Nested
    @DisplayName("POST /auth/signup")
    class SignupTests {

        @Test
        @DisplayName("returns 200 with valid registration data")
        void signupSuccess() throws Exception {
            User mockUser = new User();
            mockUser.setEmail("test@example.com");
            when(authenticationService.signup(any(RegisterUserDto.class))).thenReturn(mockUser);

            mockMvc.perform(post("/auth/signup")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"email\":\"test@example.com\",\"password\":\"secret123\",\"username\":\"testuser\"}"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.email").value("test@example.com"))
                    .andExpect(jsonPath("$.message").exists());
        }

        @Test
        @DisplayName("returns 400 when email is blank")
        void signupBlankEmail() throws Exception {
            mockMvc.perform(post("/auth/signup")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"email\":\"\",\"password\":\"secret123\"}"))
                    .andExpect(status().isBadRequest());
        }

        @Test
        @DisplayName("returns 400 when email format is invalid")
        void signupInvalidEmail() throws Exception {
            mockMvc.perform(post("/auth/signup")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"email\":\"not-an-email\",\"password\":\"secret123\"}"))
                    .andExpect(status().isBadRequest());
        }

        @Test
        @DisplayName("returns 400 when password is too short")
        void signupShortPassword() throws Exception {
            mockMvc.perform(post("/auth/signup")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"email\":\"test@example.com\",\"password\":\"abc\"}"))
                    .andExpect(status().isBadRequest());
        }

        @Test
        @DisplayName("returns 400 when password is missing")
        void signupMissingPassword() throws Exception {
            mockMvc.perform(post("/auth/signup")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"email\":\"test@example.com\"}"))
                    .andExpect(status().isBadRequest());
        }
    }

    @Nested
    @DisplayName("POST /auth/login")
    class LoginTests {

        @Test
        @DisplayName("returns 200 with JWT token on valid login")
        void loginSuccess() throws Exception {
            User mockUser = new User();
            mockUser.setEmail("test@example.com");
            when(authenticationService.authenticate(any(LogInUserDto.class))).thenReturn(mockUser);
            when(jwtService.generateToken(any(User.class))).thenReturn("mock-jwt-token");
            when(jwtService.getExpirationTime()).thenReturn(3600000L);

            mockMvc.perform(post("/auth/login")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"email\":\"test@example.com\",\"password\":\"secret123\"}"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.token").value("mock-jwt-token"))
                    .andExpect(jsonPath("$.expiresIn").value(3600000));
        }

        @Test
        @DisplayName("returns 400 when email is blank")
        void loginBlankEmail() throws Exception {
            mockMvc.perform(post("/auth/login")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"email\":\"\",\"password\":\"secret123\"}"))
                    .andExpect(status().isBadRequest());
        }

        @Test
        @DisplayName("returns 400 when password is blank")
        void loginBlankPassword() throws Exception {
            mockMvc.perform(post("/auth/login")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"email\":\"test@example.com\",\"password\":\"\"}"))
                    .andExpect(status().isBadRequest());
        }
    }

    @Nested
    @DisplayName("POST /auth/verify")
    class VerifyTests {

        @Test
        @DisplayName("returns 200 on successful verification")
        void verifySuccess() throws Exception {
            mockMvc.perform(post("/auth/verify")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"email\":\"test@example.com\",\"verificationCode\":123456}"))
                    .andExpect(status().isOk());
        }

        @Test
        @DisplayName("returns 400 when email is invalid")
        void verifyInvalidEmail() throws Exception {
            mockMvc.perform(post("/auth/verify")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"email\":\"bad-email\",\"verificationCode\":123456}"))
                    .andExpect(status().isBadRequest());
        }

        @Test
        @DisplayName("returns 400 when verification code is missing")
        void verifyMissingCode() throws Exception {
            mockMvc.perform(post("/auth/verify")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"email\":\"test@example.com\"}"))
                    .andExpect(status().isBadRequest());
        }
    }
}
